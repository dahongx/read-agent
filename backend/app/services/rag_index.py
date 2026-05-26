from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pypdf import PdfReader
from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.models import SessionSourceDoc

logger = logging.getLogger(__name__)

_CHUNK_TARGET_CHARS = 1200
_CHUNK_MIN_CHARS = 200
_BM25_CORPUS_FILENAME = "bm25_corpus.json"

_EMBED_MODEL_CACHE: HuggingFaceEmbedding | None = None
_BM25_CACHE: dict[str, tuple[float, list[dict[str, Any]], BM25Okapi]] = {}


def _resolve_embed_model_name() -> str:
    model_path = settings.embed_model_path
    if model_path.exists():
        return str(model_path)
    return settings.EMBED_MODEL_NAME


def _get_embed_model() -> HuggingFaceEmbedding:
    global _EMBED_MODEL_CACHE
    if _EMBED_MODEL_CACHE is None:
        settings.embed_cache_path.mkdir(parents=True, exist_ok=True)
        _EMBED_MODEL_CACHE = HuggingFaceEmbedding(
            model_name=_resolve_embed_model_name(),
            cache_folder=str(settings.embed_cache_path),
            trust_remote_code=True,
        )
    return _EMBED_MODEL_CACHE


def _extract_title(reader: PdfReader, first_page_text: str) -> str:
    meta = reader.metadata
    if meta and meta.title and len(meta.title.strip()) > 5:
        return meta.title.strip()

    for line in first_page_text.splitlines():
        line = line.strip()
        if not line or len(line) < 6:
            continue
        if re.match(r"^(arXiv|http|doi|\d)", line, re.IGNORECASE):
            continue
        if line.count(",") > 3:
            continue
        if line[0].isupper() and len(line) > 8:
            return line[:200]

    return Path(reader.stream.name).stem if hasattr(reader.stream, "name") else "Unknown Paper"  # type: ignore[attr-defined]


def _split_into_paragraphs(text: str) -> list[str]:
    text = re.sub(r"\n{3,}", "\n\n", text)
    raw = re.split(r"\n\n+", text)
    paragraphs: list[str] = []

    for para in raw:
        para = para.strip()
        para = re.sub(r"(\w)-\n(\w)", r"\1\2", para)
        para = para.replace("\n", " ")
        para = re.sub(r"  +", " ", para)
        if para:
            paragraphs.append(para)

    return paragraphs


def _group_paragraphs(
    paragraphs: list[str],
    page_num: int,
    file_name: str,
    paper_title: str,
    metadata_extra: dict[str, Any] | None = None,
) -> list[TextNode]:
    nodes: list[TextNode] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        if current_parts:
            metadata = {
                "page_label": str(page_num),
                "page_number": page_num,
                "file_name": file_name,
                "paper_title": paper_title,
                **(metadata_extra or {}),
            }
            nodes.append(
                TextNode(
                    text="\n\n".join(current_parts),
                    metadata=metadata,
                )
            )

    for para in paragraphs:
        if len(para) < 30 and not para[0].islower():
            continue

        current_parts.append(para)
        current_len += len(para)

        if current_len >= _CHUNK_TARGET_CHARS:
            flush()
            current_parts = []
            current_len = 0

    if current_parts:
        remainder = "\n\n".join(current_parts)
        if nodes and current_len < _CHUNK_MIN_CHARS:
            nodes[-1] = TextNode(
                text=nodes[-1].text + "\n\n" + remainder,
                metadata=nodes[-1].metadata,
            )
        else:
            flush()

    return nodes


def _build_nodes(pdf_path: str, metadata_extra: dict[str, Any] | None = None) -> list[TextNode]:
    reader = PdfReader(pdf_path)
    file_name = Path(pdf_path).name

    first_page_text = reader.pages[0].extract_text() or "" if reader.pages else ""
    paper_title = _extract_title(reader, first_page_text)
    logger.info("Detected paper title: %s", paper_title)

    repeated_lines: set[str] = set()
    if len(reader.pages) >= 3:
        def first_lines(page_idx: int) -> list[str]:
            text = reader.pages[page_idx].extract_text() or ""
            return [line.strip() for line in text.splitlines()[:3] if line.strip()]

        from collections import Counter

        sets = [set(first_lines(i)) for i in range(min(4, len(reader.pages)))]
        counts = Counter(line for lines in sets for line in lines)
        repeated_lines = {line for line, cnt in counts.items() if cnt >= 3 and len(line) > 5}
        if repeated_lines:
            logger.info("Detected repeated header lines: %s", repeated_lines)

    all_nodes: list[TextNode] = []
    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue

        lines = raw_text.splitlines()
        cleaned_lines = [line for line in lines if line.strip() not in repeated_lines]
        cleaned_text = "\n".join(cleaned_lines)

        paragraphs = _split_into_paragraphs(cleaned_text)
        all_nodes.extend(_group_paragraphs(paragraphs, page_num, file_name, paper_title, metadata_extra))

    logger.info(
        "Built %d paragraph-based chunks from %d pages (title: %s)",
        len(all_nodes),
        len(reader.pages),
        paper_title,
    )
    return all_nodes


def _tokenize(text: str) -> list[str]:
    """BM25 tokenizer：中文按字切，英文按 word 切，丢弃标点。"""
    text = text.lower()
    tokens: list[str] = []
    buf: list[str] = []
    for ch in text:
        if "一" <= ch <= "鿿":
            if buf:
                tokens.append("".join(buf))
                buf = []
            tokens.append(ch)
        elif ch.isalnum():
            buf.append(ch)
        else:
            if buf:
                tokens.append("".join(buf))
                buf = []
    if buf:
        tokens.append("".join(buf))
    return tokens


def _persist_bm25_corpus(index_dir: str, nodes: list[TextNode]) -> None:
    corpus_path = Path(index_dir) / _BM25_CORPUS_FILENAME
    payload = [
        {
            "node_id": node.node_id,
            "text": node.get_content(),
            "metadata": node.metadata,
        }
        for node in nodes
    ]
    corpus_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    logger.info("BM25 corpus persisted: %s (%d entries)", corpus_path, len(payload))


def _load_bm25(index_dir: str) -> tuple[list[dict[str, Any]], BM25Okapi] | None:
    corpus_path = Path(index_dir) / _BM25_CORPUS_FILENAME
    if not corpus_path.exists():
        return None

    mtime = corpus_path.stat().st_mtime
    cached = _BM25_CACHE.get(index_dir)
    if cached and cached[0] == mtime:
        return cached[1], cached[2]

    try:
        payload = json.loads(corpus_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read BM25 corpus: %s", corpus_path)
        return None

    if not payload:
        return None

    tokenized = [_tokenize(entry["text"]) for entry in payload]
    bm25 = BM25Okapi(tokenized)
    _BM25_CACHE[index_dir] = (mtime, payload, bm25)
    return payload, bm25


def build_multi_index(source_docs: list[SessionSourceDoc], index_dir: str) -> None:
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Building multi-doc RAG index into %s (%d docs)", index_dir, len(source_docs))

    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    all_nodes: list[TextNode] = []
    for source_doc in sorted(source_docs, key=lambda doc: doc.order):
        metadata_extra = {
            "doc_id": source_doc.doc_id,
            "doc_order": source_doc.order,
            "source_file_name": source_doc.source_file_name,
            "content_hash": source_doc.content_hash,
        }
        nodes = _build_nodes(source_doc.pdf_path, metadata_extra=metadata_extra)
        all_nodes.extend(nodes)
        logger.info(
            "Added %d nodes for %s (doc_id=%s)",
            len(nodes),
            source_doc.source_file_name,
            source_doc.doc_id,
        )

    index = VectorStoreIndex(all_nodes, show_progress=False)
    index.storage_context.persist(persist_dir=index_dir)
    _persist_bm25_corpus(index_dir, all_nodes)
    logger.info("Multi-doc index persisted to %s (%d nodes, %d docs)", index_dir, len(all_nodes), len(source_docs))


def build_index(pdf_path: str, index_dir: str) -> None:
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Building RAG index: %s -> %s", pdf_path, index_dir)

    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    nodes = _build_nodes(pdf_path)
    index = VectorStoreIndex(nodes, show_progress=False)
    index.storage_context.persist(persist_dir=index_dir)
    _persist_bm25_corpus(index_dir, nodes)
    logger.info("Index persisted to %s (%d nodes)", index_dir, len(nodes))


def _node_to_chunk(text: str, meta: dict[str, Any]) -> dict[str, Any]:
    file_name = meta.get("file_name", "unknown")
    paper_title = meta.get("paper_title", file_name)
    page = meta.get("page_label") or meta.get("page_number")
    if isinstance(page, str) and page.isdigit():
        page = int(page)
    return {
        "text": text[:400] + ("..." if len(text) > 400 else ""),
        "full_text": text,
        "file": paper_title,
        "page": page,
        "doc_id": meta.get("doc_id"),
        "doc_order": meta.get("doc_order"),
        "source_file_name": meta.get("source_file_name", file_name),
    }


def _rrf_merge(
    rankings: list[list[str]],
    *,
    k: int = 60,
) -> list[tuple[str, float]]:
    """Reciprocal Rank Fusion."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, node_id in enumerate(ranking, start=1):
            scores[node_id] = scores.get(node_id, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda item: item[1], reverse=True)


def query_index(index_dir: str, question: str) -> list[dict[str, Any]]:
    """Hybrid retrieval：dense + BM25 → RRF → 返回前 N 个候选（未 rerank）。"""
    started = time.time()
    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    storage_context = StorageContext.from_defaults(persist_dir=index_dir)
    index = load_index_from_storage(storage_context)

    top_k_dense = settings.RAG_TOP_K_DENSE
    top_k_bm25 = settings.RAG_TOP_K_BM25

    retriever = VectorIndexRetriever(index=index, similarity_top_k=top_k_dense)
    dense_nodes = retriever.retrieve(question)
    dense_ranking = [node.node.node_id for node in dense_nodes]
    dense_lookup = {node.node.node_id: node.node for node in dense_nodes}

    bm25_payload = _load_bm25(index_dir)
    if bm25_payload is None:
        logger.warning("BM25 corpus missing for %s — falling back to dense-only", index_dir)
        candidates: list[dict[str, Any]] = []
        for node in dense_nodes:
            candidates.append(_node_to_chunk(node.node.get_content(), node.node.metadata or {}))
        logger.info("Hybrid retrieval (dense-only fallback) %.2fs candidates=%d", time.time() - started, len(candidates))
        return candidates

    corpus, bm25 = bm25_payload
    tokens = _tokenize(question)
    if tokens:
        bm25_scores = bm25.get_scores(tokens)
        bm25_indices = sorted(range(len(corpus)), key=lambda i: bm25_scores[i], reverse=True)[:top_k_bm25]
    else:
        bm25_indices = []
    bm25_lookup = {corpus[i]["node_id"]: corpus[i] for i in bm25_indices}
    bm25_ranking = [corpus[i]["node_id"] for i in bm25_indices]

    fused = _rrf_merge([dense_ranking, bm25_ranking])
    fused = fused[: max(top_k_dense, top_k_bm25)]

    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()
    for node_id, _score in fused:
        if node_id in seen:
            continue
        seen.add(node_id)
        if node_id in dense_lookup:
            node = dense_lookup[node_id]
            candidates.append(_node_to_chunk(node.get_content(), node.metadata or {}))
        elif node_id in bm25_lookup:
            entry = bm25_lookup[node_id]
            candidates.append(_node_to_chunk(entry["text"], entry.get("metadata") or {}))

    logger.info(
        "Hybrid retrieval %.2fs  dense=%d  bm25=%d  fused=%d",
        time.time() - started,
        len(dense_ranking),
        len(bm25_ranking),
        len(candidates),
    )
    return candidates

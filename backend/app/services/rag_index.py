from __future__ import annotations

import logging
import re
from pathlib import Path

from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pypdf import PdfReader

from app.core.config import settings

logger = logging.getLogger(__name__)

_SIMILARITY_TOP_K = 6

# Target chunk size in characters (~300-400 tokens)
_CHUNK_TARGET_CHARS = 1200
_CHUNK_MIN_CHARS = 200

_EMBED_MODEL_CACHE: HuggingFaceEmbedding | None = None


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
    """Extract paper title from PDF metadata or first-page heuristic."""
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
    """Split page text into natural paragraphs."""
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
) -> list[TextNode]:
    """Group paragraphs into balanced chunks with metadata."""
    nodes: list[TextNode] = []
    current_parts: list[str] = []
    current_len = 0

    def flush() -> None:
        if current_parts:
            nodes.append(
                TextNode(
                    text="\n\n".join(current_parts),
                    metadata={
                        "page_label": str(page_num),
                        "file_name": file_name,
                        "paper_title": paper_title,
                    },
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


def _build_nodes(pdf_path: str) -> list[TextNode]:
    """Parse PDF into paragraph-based TextNodes with paper title metadata."""
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
        all_nodes.extend(_group_paragraphs(paragraphs, page_num, file_name, paper_title))

    logger.info(
        "Built %d paragraph-based chunks from %d pages (title: %s)",
        len(all_nodes),
        len(reader.pages),
        paper_title,
    )
    return all_nodes


def build_index(pdf_path: str, index_dir: str) -> None:
    """Parse PDF into paragraph chunks, embed, and persist index."""
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Building RAG index: %s -> %s", pdf_path, index_dir)

    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    nodes = _build_nodes(pdf_path)
    index = VectorStoreIndex(nodes, show_progress=False)
    index.storage_context.persist(persist_dir=index_dir)
    logger.info("Index persisted to %s (%d nodes)", index_dir, len(nodes))


def query_index(index_dir: str, question: str) -> list[dict]:
    """Load persisted index and retrieve paragraph chunks by pure vector similarity."""
    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    storage_context = StorageContext.from_defaults(persist_dir=index_dir)
    index = load_index_from_storage(storage_context)

    retriever = VectorIndexRetriever(index=index, similarity_top_k=_SIMILARITY_TOP_K)
    nodes = retriever.retrieve(question)

    if not nodes:
        return []

    results: list[dict] = []
    for node in nodes:
        text = node.node.get_content()
        meta = node.node.metadata or {}
        file_name = meta.get("file_name", "unknown")
        paper_title = meta.get("paper_title", file_name)
        page = meta.get("page_label") or meta.get("page_number")
        if isinstance(page, str) and page.isdigit():
            page = int(page)

        results.append({
            "text": text[:400] + ("..." if len(text) > 400 else ""),
            "full_text": text,
            "file": paper_title,
            "page": page,
        })

    return results

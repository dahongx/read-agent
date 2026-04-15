from __future__ import annotations

import logging
import re
from pathlib import Path

from llama_index.core import Settings, StorageContext, VectorStoreIndex, load_index_from_storage
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import TextNode
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from pypdf import PdfReader

logger = logging.getLogger(__name__)

_SIMILARITY_TOP_K = 6
_EMBED_MODEL_NAME = "BAAI/bge-m3"

# Target chunk size in characters (~300-400 tokens)
_CHUNK_TARGET_CHARS = 1200
_CHUNK_MIN_CHARS = 200   # don't create tiny orphan chunks


def _get_embed_model() -> HuggingFaceEmbedding:
    return HuggingFaceEmbedding(model_name=_EMBED_MODEL_NAME, trust_remote_code=True)


def _extract_title(reader: PdfReader, first_page_text: str) -> str:
    """Extract paper title from PDF metadata or first-page heuristic."""
    meta = reader.metadata
    if meta and meta.title and len(meta.title.strip()) > 5:
        return meta.title.strip()
    # Heuristic: find the first meaningful line on page 1
    for line in first_page_text.splitlines():
        line = line.strip()
        if not line or len(line) < 6:
            continue
        # Skip arXiv IDs, URLs, dates, author lines
        if re.match(r'^(arXiv|http|doi|\d)', line, re.I):
            continue
        # Skip lines that look like author/institution (contain digits/commas densely)
        if line.count(',') > 3:
            continue
        if line[0].isupper() and len(line) > 8:
            return line[:200]
    return Path(reader.stream.name).stem if hasattr(reader.stream, 'name') else 'Unknown Paper'  # type: ignore[attr-defined]


def _split_into_paragraphs(text: str) -> list[str]:
    """Split page text into natural paragraphs."""
    # Normalize: collapse 3+ newlines to 2
    text = re.sub(r'\n{3,}', '\n\n', text)
    # Split on blank lines
    raw = re.split(r'\n\n+', text)
    paragraphs = []
    for p in raw:
        p = p.strip()
        # Merge hyphenated line breaks typical of PDF columns: "meth-\nod" → "method"
        p = re.sub(r'(\w)-\n(\w)', r'\1\2', p)
        # Replace single newlines within a paragraph with space
        p = p.replace('\n', ' ')
        # Collapse multiple spaces
        p = re.sub(r'  +', ' ', p)
        if p:
            paragraphs.append(p)
    return paragraphs


def _group_paragraphs(paragraphs: list[str], page_num: int,
                      file_name: str, paper_title: str) -> list[TextNode]:
    """Group paragraphs into balanced chunks with metadata."""
    nodes: list[TextNode] = []
    current_parts: list[str] = []
    current_len = 0

    def flush():
        if current_parts:
            text = '\n\n'.join(current_parts)
            nodes.append(TextNode(
                text=text,
                metadata={
                    'page_label': str(page_num),
                    'file_name': file_name,
                    'paper_title': paper_title,
                }
            ))

    for para in paragraphs:
        # Skip very short lines that are likely headers/footers/page numbers
        if len(para) < 30 and not para[0].islower():
            continue

        current_parts.append(para)
        current_len += len(para)

        if current_len >= _CHUNK_TARGET_CHARS:
            flush()
            current_parts = []
            current_len = 0

    # Flush remainder — if tiny, merge into last node
    if current_parts:
        remainder = '\n\n'.join(current_parts)
        if nodes and current_len < _CHUNK_MIN_CHARS:
            # Append to previous chunk instead of creating a tiny orphan
            nodes[-1] = TextNode(
                text=nodes[-1].text + '\n\n' + remainder,
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

    # Lines that repeat on every page (e.g. running header = paper title)
    # Collect candidate repeated lines by comparing first lines of several pages
    repeated_lines: set[str] = set()
    if len(reader.pages) >= 3:
        def first_lines(page_idx: int) -> list[str]:
            t = reader.pages[page_idx].extract_text() or ""
            return [l.strip() for l in t.splitlines()[:3] if l.strip()]

        sets = [set(first_lines(i)) for i in range(min(4, len(reader.pages)))]
        # Lines appearing on 3+ pages are likely headers
        from collections import Counter
        counts = Counter(line for s in sets for line in s)
        repeated_lines = {line for line, cnt in counts.items() if cnt >= 3 and len(line) > 5}
        if repeated_lines:
            logger.info("Detected repeated header lines: %s", repeated_lines)

    all_nodes: list[TextNode] = []
    for page_num, page in enumerate(reader.pages, start=1):
        raw_text = page.extract_text() or ""
        if not raw_text.strip():
            continue

        # Remove repeated header lines from this page
        lines = raw_text.splitlines()
        cleaned_lines = [l for l in lines if l.strip() not in repeated_lines]
        cleaned_text = '\n'.join(cleaned_lines)

        paragraphs = _split_into_paragraphs(cleaned_text)
        nodes = _group_paragraphs(paragraphs, page_num, file_name, paper_title)
        all_nodes.extend(nodes)

    logger.info("Built %d paragraph-based chunks from %d pages (title: %s)",
                len(all_nodes), len(reader.pages), paper_title)
    return all_nodes


def build_index(pdf_path: str, index_dir: str) -> None:
    """Parse PDF into paragraph chunks, embed, and persist index."""
    Path(index_dir).mkdir(parents=True, exist_ok=True)
    logger.info("Building RAG index: %s → %s", pdf_path, index_dir)

    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    nodes = _build_nodes(pdf_path)
    index = VectorStoreIndex(nodes, show_progress=False)
    index.storage_context.persist(persist_dir=index_dir)
    logger.info("Index persisted to %s (%d nodes)", index_dir, len(nodes))


def query_index(index_dir: str, question: str) -> tuple[str, list[dict]]:
    """Load persisted index and retrieve relevant chunks."""
    Settings.embed_model = _get_embed_model()
    Settings.llm = None

    storage_context = StorageContext.from_defaults(persist_dir=index_dir)
    index = load_index_from_storage(storage_context)

    retriever = VectorIndexRetriever(index=index, similarity_top_k=_SIMILARITY_TOP_K)
    nodes = retriever.retrieve(question)

    if not nodes:
        return "", []

    context_parts: list[str] = []
    sources: list[dict] = []

    for node in nodes:
        text = node.node.get_content()
        meta = node.node.metadata or {}
        file_name = meta.get("file_name", "unknown")
        paper_title = meta.get("paper_title", file_name)
        page = meta.get("page_label") or meta.get("page_number")
        if isinstance(page, str) and page.isdigit():
            page = int(page)

        context_parts.append(f"[来自《{paper_title}》第{page}页]\n{text}")
        sources.append({
            "text": text[:400] + ("..." if len(text) > 400 else ""),
            "file": paper_title,   # show title instead of filename
            "page": page,
        })

    return "\n\n---\n\n".join(context_parts), sources

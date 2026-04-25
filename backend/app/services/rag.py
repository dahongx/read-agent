from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.services import session_store

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 4000


def _build_context_and_sources(chunks: list[dict]) -> tuple[str, list[dict]]:
    context_parts: list[str] = []
    sources: list[dict] = []

    for chunk in chunks:
        full_text = (chunk.get("full_text") or chunk.get("text") or "").strip()
        preview_text = (chunk.get("text") or "").strip()
        if not preview_text:
            preview_text = full_text[:400] + ("..." if len(full_text) > 400 else "")

        file_name = chunk.get("file", "unknown")
        page = chunk.get("page")
        page_label = f"第{page}页" if isinstance(page, int) else "页码未知"
        source_file_name = chunk.get("source_file_name")
        doc_id = chunk.get("doc_id")
        doc_order = chunk.get("doc_order")

        context_parts.append(f"[来自《{file_name}》{page_label}]\n{full_text}")
        sources.append({
            "text": preview_text,
            "file": file_name,
            "page": page,
            "doc_id": doc_id,
            "doc_order": doc_order,
            "source_file_name": source_file_name,
        })

    return "\n\n---\n\n".join(context_parts), sources


def retrieve(session_id: str, question: str) -> tuple[str, list[dict]]:
    """
    Returns (context_text, sources).
    DEV_MODE: reads fixture design_spec.md as quick stub context.
    Real mode: queries the persisted RAG index built during ingestion.
    """
    if settings.DEV_MODE_RAG:
        spec_path = settings.fixture_path / "design_spec.md"
        if spec_path.exists():
            text = spec_path.read_text(encoding="utf-8")[:_MAX_CONTEXT_CHARS]
            sources = [{
                "text": text[:300] + ("..." if len(text) > 300 else ""),
                "file": "design_spec.md",
                "page": None,
                "doc_id": None,
                "doc_order": None,
                "source_file_name": "design_spec.md",
            }]
            logger.info("DEV_MODE RAG: using fixture design_spec.md (%d chars)", len(text))
            return text, sources
        logger.warning("DEV_MODE RAG: design_spec.md not found in fixture")
        return "", []

    session = session_store.get_session(session_id)
    if not session or not session.rag_index_path:
        logger.warning("No RAG index for session %s", session_id)
        return "", []

    index_dir = session.rag_index_path
    if not Path(index_dir).exists():
        logger.warning("RAG index dir not found: %s", index_dir)
        return "", []

    from app.services.rag_index import query_index

    chunks = query_index(index_dir, question)
    if not chunks:
        return "", []

    return _build_context_and_sources(chunks)

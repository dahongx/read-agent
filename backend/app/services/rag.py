from __future__ import annotations

import logging
from pathlib import Path

from app.core.config import settings
from app.services import session_store

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 4000


def retrieve(session_id: str, question: str) -> tuple[str, list[dict]]:
    """
    Returns (context_text, sources).
    DEV_MODE: reads fixture design_spec.md as quick stub context.
    Real mode: queries the LlamaIndex vector index built during ingestion.
    """
    if settings.DEV_MODE_RAG:
        spec_path = settings.fixture_path / "design_spec.md"
        if spec_path.exists():
            text = spec_path.read_text(encoding="utf-8")[:_MAX_CONTEXT_CHARS]
            sources = [{"text": text[:300] + "...", "file": "design_spec.md", "page": None}]
            logger.info("DEV_MODE RAG: using fixture design_spec.md (%d chars)", len(text))
            return text, sources
        logger.warning("DEV_MODE RAG: design_spec.md not found in fixture")
        return "", []

    # Real mode: use LlamaIndex
    session = session_store.get_session(session_id)
    if not session or not session.rag_index_path:
        logger.warning("No RAG index for session %s", session_id)
        return "", []

    index_dir = session.rag_index_path
    if not Path(index_dir).exists():
        logger.warning("RAG index dir not found: %s", index_dir)
        return "", []

    from app.services.rag_index import query_index
    return query_index(index_dir, question)

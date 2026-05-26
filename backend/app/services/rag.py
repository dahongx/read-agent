from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Iterable, Optional

from app.core.config import settings
from app.services import session_store

logger = logging.getLogger(__name__)

_MAX_CONTEXT_CHARS = 4000


def _build_context_and_sources(chunks: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    context_parts: list[str] = []
    sources: list[dict[str, Any]] = []

    for idx, chunk in enumerate(chunks, start=1):
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

        context_parts.append(f"[片段{idx} | 来自《{file_name}》{page_label}]\n{full_text}")
        sources.append({
            "chunk_id": idx,
            "text": preview_text,
            "full_text": full_text,
            "file": file_name,
            "page": page,
            "doc_id": doc_id,
            "doc_order": doc_order,
            "source_file_name": source_file_name,
            "rerank_score": chunk.get("rerank_score"),
        })

    return "\n\n---\n\n".join(context_parts), sources


def _chunk_key(chunk: dict[str, Any]) -> tuple:
    """Key used to dedupe chunks across multiple subqueries."""
    return (
        chunk.get("doc_id"),
        chunk.get("source_file_name") or chunk.get("file"),
        chunk.get("page"),
        (chunk.get("full_text") or "")[:120],
    )


def _filter_by_doc(chunks: list[dict[str, Any]], doc_id: str) -> list[dict[str, Any]]:
    return [c for c in chunks if (c.get("doc_id") == doc_id)]


def _retrieve_one(
    index_dir: str,
    query: str,
    *,
    final_k: int,
    doc_id: str | None = None,
) -> list[dict[str, Any]]:
    """单 query：query_index → 可选 doc 过滤 → rerank 取 top final_k。"""
    from app.services.rag_index import query_index
    from app.services.reranker import rerank

    candidates = query_index(index_dir, query)
    if not candidates:
        return []
    if doc_id:
        filtered = _filter_by_doc(candidates, doc_id)
        # 万一 doc 过滤后空了（doc_id 写错或 metadata 缺失），退化用全部
        if filtered:
            candidates = filtered
        else:
            logger.warning("doc filter doc_id=%s removed all candidates, falling back", doc_id)
    return rerank(query, candidates, top_k=final_k)


def retrieve_from_index(
    index_dir: str,
    question: str,
    *,
    plan: Optional[Any] = None,
) -> tuple[str, list[dict[str, Any]]]:
    """
    对 RAG 索引执行检索。
    - plan=None 或单一 subquery 单一 scope：直接 hybrid+rerank
    - plan.scope=single：按 doc_id 过滤后单 query
    - plan.scope=all + 多 subquery：每个 subquery 独立 retrieve+rerank，合并去重
    """
    if not Path(index_dir).exists():
        logger.warning("RAG index dir not found: %s", index_dir)
        return "", []

    final_k = settings.RAG_TOP_K_FINAL

    if plan is None or not getattr(plan, "subqueries", None):
        chunks = _retrieve_one(index_dir, question, final_k=final_k)
        return _build_context_and_sources(chunks)

    scope = getattr(plan, "scope", "all")
    subqueries: list[str] = list(plan.subqueries)

    if scope == "single":
        # 单 doc，单 query 即可
        sub_q = subqueries[0] if subqueries else question
        chunks = _retrieve_one(index_dir, sub_q, final_k=final_k, doc_id=plan.doc_id)
        return _build_context_and_sources(chunks)

    # scope=all：多个 subquery 分别检索
    if len(subqueries) == 1:
        chunks = _retrieve_one(index_dir, subqueries[0], final_k=final_k)
        return _build_context_and_sources(chunks)

    per_query_k = max(2, final_k // max(1, len(subqueries)) + 1)
    merged: list[dict[str, Any]] = []
    seen: set[tuple] = set()

    for sub_q in subqueries:
        sub_chunks = _retrieve_one(index_dir, sub_q, final_k=per_query_k)
        for chunk in sub_chunks:
            key = _chunk_key(chunk)
            if key in seen:
                continue
            seen.add(key)
            merged.append(chunk)

    if not merged:
        return "", []

    # 取前 final_k 条；保持 subquery 顺序作为 doc 间均衡的来源
    merged = merged[:final_k]
    return _build_context_and_sources(merged)


def retrieve(session_id: str, question: str) -> tuple[str, list[dict[str, Any]]]:
    """会话路径：DEV_MODE_RAG 走 fixture；正常模式从 session_store 取 index_dir。"""
    if settings.DEV_MODE_RAG:
        spec_path = settings.fixture_path / "design_spec.md"
        if spec_path.exists():
            text = spec_path.read_text(encoding="utf-8")[:_MAX_CONTEXT_CHARS]
            sources = [{
                "chunk_id": 1,
                "text": text[:300] + ("..." if len(text) > 300 else ""),
                "full_text": text,
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

    return retrieve_from_index(session.rag_index_path, question)

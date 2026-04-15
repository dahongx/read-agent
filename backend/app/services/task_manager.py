from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.core.config import settings
from app.models import PptConfig, SessionStatus
from app.services import session_store
from app.services.connection_manager import manager as ws_manager

logger = logging.getLogger(__name__)


async def _broadcast_progress(session_id: str, task: str, step: str, pct: int) -> None:
    session_store.update_progress(session_id, task, step, pct)
    conns = len(ws_manager._connections.get(session_id, []))
    logger.info("[PROGRESS][%s] task=%s pct=%d step=%r  ws_clients=%d", session_id, task, pct, step, conns)
    await ws_manager.broadcast(session_id, {
        "event": "progress",
        "task": task,
        "step": step,
        "pct": pct,
    })


async def _ppt_task(session_id: str, pdf_path: str, config: PptConfig) -> str:
    from app.services.ppt_generator import compute_cache_key, run_paper_to_ppt

    await _broadcast_progress(session_id, "ppt", "检查缓存", 5)

    cache_key = compute_cache_key(pdf_path, config)
    cache_dir = settings.ppt_cache_path / cache_key
    logger.info("[PPT_TASK][%s] cache_key=%s  cache_dir=%s", session_id, cache_key, cache_dir)

    # Cache hit: only valid if svg_final/ has SVGs AND a .pptx exists
    existing = _find_project_dir(cache_dir)
    logger.info("[PPT_TASK][%s] cache lookup result: %s", session_id, existing)
    if existing:
        pptx_files = [p for p in existing.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
        if not pptx_files:
            pptx_files = list(existing.glob("*.pptx"))
        if pptx_files:
            logger.info("[PPT_TASK][%s] CACHE HIT → %s", session_id, pptx_files[0])
            await _broadcast_progress(session_id, "ppt", "使用已有 PPT（配置未变更）", 100)
            return str(pptx_files[0])
        else:
            # svg_final exists but no pptx — incomplete previous run, regenerate
            logger.info("[PPT_TASK][%s] Cache partial (svg_final found but no pptx), regenerating", session_id)

    cache_dir.mkdir(parents=True, exist_ok=True)
    logger.info("[PPT_TASK][%s] CACHE MISS → calling Claude CLI", session_id)

    # Run Claude CLI to generate PPT
    project_dir = await run_paper_to_ppt(
        session_id, pdf_path, config, cache_dir, _broadcast_progress
    )

    await _broadcast_progress(session_id, "ppt", "PPT 生成完成", 100)

    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))
    logger.info("[PPT_TASK][%s] pptx files found: %s", session_id, pptx_files)
    return str(pptx_files[0]) if pptx_files else str(project_dir)


def _find_project_dir(cache_dir: Path) -> Path | None:
    """Find a valid generated project directory (has svg_final/ with SVGs)."""
    if not cache_dir.exists():
        return None
    # Direct: cache_dir itself is the project
    if (cache_dir / "svg_final").exists() and any((cache_dir / "svg_final").glob("*.svg")):
        return cache_dir
    # Nested: Claude created a subdir
    for d in sorted(cache_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir() and (d / "svg_final").exists() and any((d / "svg_final").glob("*.svg")):
            return d
    return None


async def _rag_task(session_id: str, pdf_path: str) -> str:
    import hashlib
    from app.services.rag_index import build_index

    _CACHE_VERSION = "v3"

    await _broadcast_progress(session_id, "rag", "检查索引缓存", 5)
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    pdf_hash = h.hexdigest()[:16]

    cache_dir = settings.upload_path / "rag_cache" / f"{pdf_hash}-{_CACHE_VERSION}"
    index_dir = str(cache_dir)
    logger.info("[RAG_TASK][%s] pdf_hash=%s  cache_dir=%s", session_id, pdf_hash, cache_dir)

    if cache_dir.exists() and (cache_dir / "docstore.json").exists():
        logger.info("[RAG_TASK][%s] CACHE HIT → %s", session_id, index_dir)
        await _broadcast_progress(session_id, "rag", "使用已有索引", 100)
        return index_dir

    logger.info("[RAG_TASK][%s] CACHE MISS → building index", session_id)
    await _broadcast_progress(session_id, "rag", "解析 PDF", 10)
    loop = asyncio.get_event_loop()
    await _broadcast_progress(session_id, "rag", "向量化中（需要一点时间）", 40)
    try:
        await loop.run_in_executor(None, lambda: build_index(pdf_path, index_dir))
        logger.info("[RAG_TASK][%s] Index built successfully → %s", session_id, index_dir)
    except Exception as e:
        logger.exception("[RAG_TASK][%s] build_index FAILED: %s", session_id, e)
        raise
    await _broadcast_progress(session_id, "rag", "索引构建完成", 100)
    return index_dir


async def run_tasks(session_id: str, pdf_path: str, config: PptConfig | None = None) -> None:
    if config is None:
        config = PptConfig()

    logger.info(
        "[TASK][%s] run_tasks START  pdf=%s  config=%s",
        session_id, pdf_path, config.model_dump(),
    )

    session_store.update_status(session_id, SessionStatus.processing)
    await ws_manager.broadcast(session_id, {"event": "status", "status": "processing"})

    try:
        logger.info("[TASK][%s] Launching PPT + RAG tasks in parallel", session_id)
        ppt_coro = _ppt_task(session_id, pdf_path, config)
        rag_coro = _rag_task(session_id, pdf_path)
        ppt_path, rag_index_path = await asyncio.gather(ppt_coro, rag_coro)

        logger.info(
            "[TASK][%s] Both tasks finished  ppt_path=%s  rag=%s",
            session_id, ppt_path, rag_index_path,
        )
        session_store.set_output_paths(session_id, ppt_path=ppt_path, rag_index_path=rag_index_path)
        session_store.update_status(session_id, SessionStatus.ready)
        conns = len(ws_manager._connections.get(session_id, []))
        logger.info("[TASK][%s] Broadcasting DONE event  ws_clients=%d", session_id, conns)
        await ws_manager.broadcast(session_id, {"event": "done", "status": "ready"})
        logger.info("[TASK][%s] Session marked READY", session_id)

    except Exception as exc:
        logger.exception("[TASK][%s] Task FAILED: %s", session_id, exc)
        session_store.update_status(session_id, SessionStatus.error, error=str(exc))
        conns = len(ws_manager._connections.get(session_id, []))
        logger.info("[TASK][%s] Broadcasting error to %d ws clients", session_id, conns)
        await ws_manager.broadcast(session_id, {"event": "error", "message": str(exc)})

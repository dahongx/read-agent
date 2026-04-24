from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from app.models import PptConfig, SessionError, SessionStatus
from app.services import session_store
from app.services.connection_manager import manager as ws_manager
from app.services.session_logs import SessionLogRecorder
from app.services.session_paths import get_ppt_cache_dir, get_rag_cache_dir

logger = logging.getLogger(__name__)


async def _broadcast_progress(
    session_id: str,
    task: str,
    step: str,
    pct: int,
    *,
    stage: str | None = None,
    status: str = "running",
) -> None:
    stage_name = stage or step
    session_store.update_stage(session_id, task, stage_name, step, pct, status=status)
    conns = len(ws_manager._connections.get(session_id, []))
    logger.info("[PROGRESS][%s] task=%s pct=%d step=%r  ws_clients=%d", session_id, task, pct, step, conns)
    await ws_manager.broadcast(session_id, {
        "event": "progress",
        "task": task,
        "step": step,
        "pct": pct,
        "stage": stage_name,
        "stage_label": step,
        "progress_pct": pct,
        "status": status,
    })


async def _broadcast_session_snapshot(session_id: str, *, event: str | None = None) -> None:
    session = session_store.get_session(session_id)
    if session is None:
        return
    payload = session.model_dump(mode="json")
    if event:
        payload["event"] = event
    await ws_manager.broadcast(session_id, payload)


async def _log(
    recorder: SessionLogRecorder,
    *,
    source: str,
    level: str,
    stage: str,
    message: str,
    details: dict | None = None,
) -> None:
    await recorder.record(source=source, level=level, stage=stage, message=message, details=details)


async def _ppt_task(session_id: str, pdf_path: str, config: PptConfig) -> str:
    from app.services.ppt_generator import (
        compute_cache_key,
        describe_project_outputs,
        load_cached_project_outputs,
        run_ppt_generation,
        save_cached_project_outputs,
    )

    recorder = SessionLogRecorder(session_id)
    await _broadcast_progress(session_id, "ppt", "检查缓存", 5, stage="cache_check")

    cache_key = compute_cache_key(pdf_path, config)
    cache_dir = get_ppt_cache_dir(cache_key)
    logger.info("[PPT_TASK][%s] cache_key=%s  cache_dir=%s", session_id, cache_key, cache_dir)
    await _log(recorder, source="ppt", level="INFO", stage="cache_check", message="检查 PPT 缓存", details={"cache_key": cache_key})

    cached_outputs = load_cached_project_outputs(cache_dir)
    logger.info("[PPT_TASK][%s] cache manifest lookup result: %s", session_id, cached_outputs)
    if cached_outputs and cached_outputs.get("ppt_path"):
        session_store.update_path_fields(
            session_id,
            project_dir=cached_outputs.get("project_dir", ""),
            ppt_path=cached_outputs["ppt_path"],
            slides_dir=cached_outputs.get("slides_dir", ""),
            notes_dir=cached_outputs.get("notes_dir", ""),
        )
        await _log(
            recorder,
            source="ppt",
            level="INFO",
            stage="cache_check",
            message="PPT 缓存命中",
            details={"pptx": cached_outputs["ppt_path"], "project_dir": cached_outputs.get("project_dir", "")},
        )
        await _broadcast_progress(session_id, "ppt", "使用已有 PPT（配置未变更）", 100, stage="complete", status="completed")
        await _broadcast_session_snapshot(session_id)
        return cached_outputs["ppt_path"]

    await _log(recorder, source="ppt", level="INFO", stage="cache_check", message="PPT 缓存未命中，准备调用 Claude CLI", details={"cache_key": cache_key})

    project_dir = await run_ppt_generation(
        session_id,
        pdf_path,
        config,
        cache_dir,
        progress_cb=_broadcast_progress,
        log_recorder=recorder,
    )

    pptx_files = [p for p in project_dir.glob("*.pptx") if not p.name.endswith("_svg.pptx")]
    if not pptx_files:
        pptx_files = list(project_dir.glob("*.pptx"))
    logger.info("[PPT_TASK][%s] pptx files found: %s", session_id, pptx_files)
    if not pptx_files:
        raise RuntimeError("No PPTX file found after generation")

    outputs = describe_project_outputs(project_dir, str(pptx_files[0]))
    session_store.update_path_fields(
        session_id,
        project_dir=outputs["project_dir"],
        ppt_path=outputs["ppt_path"],
        slides_dir=outputs["slides_dir"],
        notes_dir=outputs["notes_dir"],
    )
    save_cached_project_outputs(cache_dir, outputs, cache_key)
    await _broadcast_progress(session_id, "ppt", "PPT 生成完成", 100, stage="complete", status="completed")
    await _log(recorder, source="ppt", level="INFO", stage="complete", message="PPT 生成完成", details=outputs)
    await _broadcast_session_snapshot(session_id)
    return str(pptx_files[0])


def _find_project_dir(cache_dir: Path) -> Path | None:
    if not cache_dir.exists():
        return None
    if (cache_dir / "svg_final").exists() and any((cache_dir / "svg_final").glob("*.svg")):
        return cache_dir
    for d in sorted(cache_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True):
        if d.is_dir() and (d / "svg_final").exists() and any((d / "svg_final").glob("*.svg")):
            return d
    return None


async def _rag_task(session_id: str, pdf_path: str) -> str:
    import hashlib
    from app.services.rag_index import build_index

    recorder = SessionLogRecorder(session_id)
    cache_version = "v3"

    await _broadcast_progress(session_id, "rag", "检查索引缓存", 5, stage="cache_check")
    await _log(recorder, source="rag", level="INFO", stage="cache_check", message="检查 RAG 缓存")
    h = hashlib.sha256()
    with open(pdf_path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    pdf_hash = h.hexdigest()[:16]

    cache_dir = get_rag_cache_dir(f"{pdf_hash}-{cache_version}")
    index_dir = str(cache_dir)
    logger.info("[RAG_TASK][%s] pdf_hash=%s  cache_dir=%s", session_id, pdf_hash, cache_dir)

    if cache_dir.exists() and (cache_dir / "docstore.json").exists():
        logger.info("[RAG_TASK][%s] CACHE HIT → %s", session_id, index_dir)
        session_store.update_path_fields(session_id, rag_index_path=index_dir)
        await _log(recorder, source="rag", level="INFO", stage="cache_check", message="RAG 缓存命中", details={"index_dir": index_dir})
        await _broadcast_progress(session_id, "rag", "使用已有索引", 100, stage="complete", status="completed")
        await _broadcast_session_snapshot(session_id)
        return index_dir

    logger.info("[RAG_TASK][%s] CACHE MISS → building index", session_id)
    await _log(recorder, source="rag", level="INFO", stage="cache_check", message="RAG 缓存未命中，开始构建索引", details={"index_dir": index_dir})
    await _broadcast_progress(session_id, "rag", "解析 PDF", 20, stage="pdf_parse")
    await _log(recorder, source="rag", level="INFO", stage="pdf_parse", message="开始解析 PDF")
    loop = asyncio.get_event_loop()
    await _broadcast_progress(session_id, "rag", "向量化中（需要一点时间）", 70, stage="embedding")
    await _log(recorder, source="rag", level="INFO", stage="embedding", message="开始向量化")

    rag_future = loop.run_in_executor(None, lambda: build_index(pdf_path, index_dir))
    timeout_seconds = 1200
    started_at = loop.time()
    try:
        while True:
            done, _ = await asyncio.wait({rag_future}, timeout=15)
            if rag_future in done:
                rag_future.result()
                logger.info("[RAG_TASK][%s] Index built successfully → %s", session_id, index_dir)
                break
            elapsed = int(loop.time() - started_at)
            await _log(
                recorder,
                source="rag",
                level="INFO",
                stage="embedding",
                message="RAG 仍在构建中",
                details={"elapsed_seconds": elapsed},
            )
            await _broadcast_progress(
                session_id,
                "rag",
                f"向量化中，已运行 {elapsed}s...",
                70,
                stage="embedding",
            )
            if elapsed >= timeout_seconds:
                err = TimeoutError(f"RAG build timed out after {timeout_seconds} seconds")
                setattr(err, "source", "rag")
                setattr(err, "stage", "embedding")
                raise err
    except Exception as e:
        if not getattr(e, "source", None):
            setattr(e, "source", "rag")
        if not getattr(e, "stage", None):
            setattr(e, "stage", "embedding")
        logger.exception("[RAG_TASK][%s] build_index FAILED: %s", session_id, e)
        await _log(recorder, source="rag", level="ERROR", stage="embedding", message="RAG 构建失败", details={"error": str(e)})
        raise
    session_store.update_path_fields(session_id, rag_index_path=index_dir)
    await _broadcast_progress(session_id, "rag", "索引构建完成", 100, stage="complete", status="completed")
    await _log(recorder, source="rag", level="INFO", stage="complete", message="索引构建完成", details={"index_dir": index_dir})
    await _broadcast_session_snapshot(session_id)
    return index_dir


async def run_tasks(session_id: str, pdf_path: str, config: PptConfig | None = None) -> None:
    if config is None:
        config = PptConfig()

    logger.info(
        "[TASK][%s] run_tasks START  pdf=%s  config=%s",
        session_id, pdf_path, config.model_dump(),
    )
    recorder = SessionLogRecorder(session_id)

    session_store.update_status(session_id, SessionStatus.processing)
    await ws_manager.broadcast(session_id, {"event": "status", "status": "processing"})
    await _broadcast_session_snapshot(session_id)
    await _log(recorder, source="system", level="INFO", stage="processing", message="开始执行 PPT 与 RAG 任务")

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
        await _log(recorder, source="system", level="INFO", stage="complete", message="会话处理完成")
        await ws_manager.broadcast(session_id, {"event": "done", "status": "ready"})
        await _broadcast_session_snapshot(session_id)
        logger.info("[TASK][%s] Session marked READY", session_id)

    except Exception as exc:
        logger.exception("[TASK][%s] Task FAILED: %s", session_id, exc)
        detail = SessionError(
            message=str(exc),
            source=getattr(exc, "source", "system"),
            stage=getattr(exc, "stage", "processing"),
            stdout_tail=getattr(exc, "stdout_tail", None),
            stderr_tail=getattr(exc, "stderr_tail", None),
        )
        session_store.set_error_detail(session_id, detail)
        session_store.update_status(session_id, SessionStatus.error, error=str(exc))
        if detail.source in {"ppt", "rag"}:
            failed_task = detail.source
            failed_label = "处理失败"
            session_store.update_stage(session_id, failed_task, detail.stage or "error", failed_label, 100, status="failed")
            other_task = "rag" if failed_task == "ppt" else "ppt"
            other_state = session_store.get_session(session_id).stages.rag if other_task == "rag" else session_store.get_session(session_id).stages.ppt
            if other_state.status == "running" and other_state.pct >= 100:
                session_store.update_stage(session_id, other_task, other_state.stage or "complete", other_state.stage_label or "完成", 100, status="completed")
        await _log(recorder, source="system", level="ERROR", stage=detail.stage or "processing", message="会话处理失败", details={"error": str(exc)})
        conns = len(ws_manager._connections.get(session_id, []))
        logger.info("[TASK][%s] Broadcasting error to %d ws clients", session_id, conns)
        await ws_manager.broadcast(session_id, {
            "event": "error",
            "message": str(exc),
            "source": detail.source,
            "stage": detail.stage,
            "stdout_tail": detail.stdout_tail,
            "stderr_tail": detail.stderr_tail,
        })
        await _broadcast_session_snapshot(session_id)

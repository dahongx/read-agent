"""Space-level read APIs：以 space_id 取产物（PPT/SVG/讲稿/PDF）。

space 是永久的（pdf_hash + config_hash），跨用户共享，URL 可分享。
"""
from __future__ import annotations

import logging
import shutil
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from app.core.config import settings
from app.services import (
    conversation_store,
    ppt_generator,
    space_store,
)
from app.services.session_paths import get_ppt_cache_dir

logger = logging.getLogger(__name__)
router = APIRouter()


def _ensure_space(space_id: str) -> dict:
    space = space_store.get(space_id)
    if not space:
        raise HTTPException(status_code=404, detail="Space not found")
    return space


def _resolve_outputs(space_id: str) -> dict:
    """从 PPT 缓存 manifest 读出 project_dir / slides_dir / notes_dir / ppt_path。"""
    cache_dir = get_ppt_cache_dir(space_id)
    cached = ppt_generator.load_cached_project_outputs(cache_dir)
    if cached:
        return cached
    return {}


@router.get("/api/users/{user_id}/spaces")
async def list_user_spaces(user_id: str) -> dict:
    spaces = space_store.list_for_user(user_id)
    items = []
    for sp in spaces:
        outputs = _resolve_outputs(sp["space_id"])
        ppt_ready = bool(outputs.get("ppt_path"))
        state = sp.get("state") or ("ready" if ppt_ready else "pending")
        items.append({
            "space_id": sp["space_id"],
            "paper_title": sp.get("paper_title"),
            "pdf_filename": sp.get("pdf_filename"),
            "session_type": sp.get("session_type", "single"),
            "config": sp.get("config"),
            "created_at": sp.get("created_at"),
            "updated_at": sp.get("updated_at"),
            "state": state,
            "error_message": sp.get("error_message"),
            "ready": ppt_ready,
        })
    return {"spaces": items, "count": len(items)}


@router.delete("/api/spaces/{space_id}")
async def delete_space_endpoint(space_id: str, user_id: str = "anonymous") -> dict:
    """删除 space 元数据 + 该用户在此空间下的会话目录。其他用户对该 space 的会话不动。"""
    deleted = space_store.delete_space(space_id)
    # 同时清理该用户在该空间的对话
    user_dir = settings.conversations_path / user_id / space_id
    if user_dir.exists():
        shutil.rmtree(user_dir, ignore_errors=True)
    return {"deleted": deleted}


@router.get("/api/spaces/{space_id}")
async def get_space(space_id: str, user_id: str = "anonymous") -> dict:
    space = _ensure_space(space_id)
    space_store.touch_access(space_id, user_id)
    outputs = _resolve_outputs(space_id)
    return {
        **space,
        "outputs": outputs,
        "ready": bool(outputs.get("ppt_path")),
    }


def _resolve_pdf_path(space: dict, doc_id: str | None = None) -> Path:
    if doc_id:
        for src in space.get("source_documents") or []:
            if src.get("doc_id") == doc_id:
                p = Path(src.get("pdf_path") or "")
                if p.exists():
                    return p
        raise HTTPException(status_code=404, detail="Source document not found")

    pdf_path = space.get("pdf_path")
    if pdf_path:
        p = Path(pdf_path)
        if p.exists():
            return p

    sources = space.get("source_documents") or []
    if sources:
        p = Path(sources[0].get("pdf_path") or "")
        if p.exists():
            return p

    raise HTTPException(status_code=404, detail="PDF file not found")


@router.get("/api/spaces/{space_id}/pdf")
async def get_space_pdf(space_id: str) -> FileResponse:
    space = _ensure_space(space_id)
    pdf_file = _resolve_pdf_path(space)
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=pdf_file.name,
        content_disposition_type="inline",
    )


@router.get("/api/spaces/{space_id}/pdf/{doc_id}")
async def get_space_source_pdf(space_id: str, doc_id: str) -> FileResponse:
    space = _ensure_space(space_id)
    pdf_file = _resolve_pdf_path(space, doc_id)
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=pdf_file.name,
        content_disposition_type="inline",
    )


@router.get("/api/spaces/{space_id}/slides")
async def get_space_slides(space_id: str) -> dict:
    _ensure_space(space_id)
    outputs = _resolve_outputs(space_id)
    slides_dir = Path(outputs.get("slides_dir") or "")
    if not slides_dir.exists():
        return {"slides": [], "count": 0}
    files = sorted(f.name for f in slides_dir.glob("*.svg"))
    return {"slides": files, "count": len(files)}


@router.get("/api/spaces/{space_id}/slides/{filename:path}")
async def get_space_slide_file(space_id: str, filename: str) -> FileResponse:
    _ensure_space(space_id)
    outputs = _resolve_outputs(space_id)
    slides_dir = Path(outputs.get("slides_dir") or "")
    if not slides_dir.exists():
        raise HTTPException(status_code=404, detail="Slides not available")
    safe_name = Path(unquote(filename)).name
    slide_path = slides_dir / safe_name
    if not slide_path.exists():
        raise HTTPException(status_code=404, detail="Slide not found")
    return FileResponse(path=str(slide_path), media_type="image/svg+xml")


@router.get("/api/spaces/{space_id}/ppt")
async def get_space_ppt(space_id: str) -> FileResponse:
    _ensure_space(space_id)
    outputs = _resolve_outputs(space_id)
    ppt_path = outputs.get("ppt_path") or ""
    ppt_file = Path(ppt_path)
    if not ppt_path or not ppt_file.exists():
        raise HTTPException(status_code=404, detail="PPT not ready yet")
    return FileResponse(
        path=str(ppt_file),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=ppt_file.name,
    )


@router.get("/api/spaces/{space_id}/script")
async def get_space_script(space_id: str) -> dict:
    _ensure_space(space_id)
    outputs = _resolve_outputs(space_id)
    notes_dir = Path(outputs.get("notes_dir") or "")
    if not notes_dir.exists():
        return {"slides": []}
    items = []
    for md in sorted(notes_dir.glob("*.md")):
        if md.name.lower() == "total.md":
            continue
        items.append({
            "filename": md.name,
            "content": md.read_text(encoding="utf-8"),
        })
    return {"slides": items}


# ────────── conversation endpoints ──────────

@router.get("/api/spaces/{space_id}/conversations")
async def list_conversations(space_id: str, user_id: str = "anonymous") -> dict:
    _ensure_space(space_id)
    items = conversation_store.list_conversations(user_id, space_id)
    return {"conversations": items, "count": len(items)}


@router.post("/api/spaces/{space_id}/conversations")
async def create_conversation_endpoint(
    space_id: str,
    user_id: str = "anonymous",
    title: str | None = None,
) -> dict:
    _ensure_space(space_id)
    try:
        conv = conversation_store.create_conversation(user_id, space_id, title=title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return conv


@router.get("/api/spaces/{space_id}/conversations/{conv_id}")
async def get_conversation_endpoint(
    space_id: str,
    conv_id: str,
    user_id: str = "anonymous",
) -> dict:
    _ensure_space(space_id)
    conv = conversation_store.get_conversation(user_id, space_id, conv_id)
    if conv is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conv


@router.patch("/api/spaces/{space_id}/conversations/{conv_id}")
async def rename_conversation_endpoint(
    space_id: str,
    conv_id: str,
    title: str,
    user_id: str = "anonymous",
) -> dict:
    _ensure_space(space_id)
    try:
        return conversation_store.rename(user_id, space_id, conv_id, title)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Conversation not found") from exc


@router.delete("/api/spaces/{space_id}/conversations/{conv_id}")
async def delete_conversation_endpoint(
    space_id: str,
    conv_id: str,
    user_id: str = "anonymous",
) -> dict:
    _ensure_space(space_id)
    deleted = conversation_store.delete_conversation(user_id, space_id, conv_id)
    return {"deleted": deleted}

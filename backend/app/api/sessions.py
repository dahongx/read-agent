from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from app.models import SessionState
from app.services import session_store
from app.services.session_logs import load_session_logs

router = APIRouter()


@router.get("/api/sessions/{session_id}", response_model=SessionState)
async def get_session(session_id: str) -> SessionState:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.get("/api/sessions/{session_id}/ppt")
async def get_session_ppt(session_id: str) -> FileResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.ppt_path:
        raise HTTPException(status_code=404, detail="PPT not ready yet")
    ppt_file = Path(session.ppt_path)
    if not ppt_file.exists():
        raise HTTPException(status_code=404, detail="PPT file not found")
    return FileResponse(
        path=str(ppt_file),
        media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        filename=ppt_file.name,
    )


@router.get("/api/sessions/{session_id}/pdf")
async def get_session_pdf(session_id: str) -> FileResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if not session.pdf_path:
        raise HTTPException(status_code=404, detail="PDF not available")
    pdf_file = Path(session.pdf_path)
    if not pdf_file.exists():
        raise HTTPException(status_code=404, detail="PDF file not found")
    return FileResponse(
        path=str(pdf_file),
        media_type="application/pdf",
        filename=pdf_file.name,
        content_disposition_type="inline",
    )


def _get_slides_dir(session_id: str) -> Path | None:
    """Return the svg_final/ directory for this session's PPT project."""
    session = session_store.get_session(session_id)
    if session is None:
        return None
    if session.paths.slides_dir:
        slides_dir = Path(session.paths.slides_dir)
        if slides_dir.exists() and any(slides_dir.glob("*.svg")):
            return slides_dir
    if not session.ppt_path:
        return None
    ppt_path = Path(session.ppt_path)
    candidates = [
        ppt_path.parent / "svg_final",
        ppt_path / "svg_final",
    ]
    for candidate in candidates:
        if candidate.exists() and any(candidate.glob("*.svg")):
            return candidate
    return None


@router.get("/api/sessions/{session_id}/slides")
async def get_slides_list(session_id: str) -> dict:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    slides_dir = _get_slides_dir(session_id)
    if slides_dir is None:
        return {"slides": [], "count": 0}
    files = sorted(f.name for f in slides_dir.glob("*.svg"))
    return {"slides": files, "count": len(files)}


@router.get("/api/sessions/{session_id}/slides/{filename:path}")
async def get_slide_file(session_id: str, filename: str) -> FileResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    slides_dir = _get_slides_dir(session_id)
    if slides_dir is None:
        raise HTTPException(status_code=404, detail="Slides not available")
    safe_name = Path(unquote(filename)).name
    slide_path = slides_dir / safe_name
    if not slide_path.exists():
        raise HTTPException(status_code=404, detail="Slide not found")
    return FileResponse(path=str(slide_path), media_type="image/svg+xml")


@router.get("/api/sessions/{session_id}/logs")
async def get_session_logs(session_id: str, limit: int = Query(default=200, ge=1, le=1000)) -> dict:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    logs = load_session_logs(session_id, limit=limit)
    return {"logs": logs, "count": len(logs)}

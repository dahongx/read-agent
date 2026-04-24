from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services import session_store
from app.services.script_gen import extract_slide_texts, generate_narrations

logger = logging.getLogger(__name__)
router = APIRouter()


class ScriptResponse(BaseModel):
    script: list[str]


def _clean_note(raw: str) -> str:
    """Keep only spoken narration lines; strip 要点/时长 metadata and [tag] prefixes."""
    lines = raw.splitlines()
    kept: list[str] = []
    for line in lines:
        s = line.strip()
        if not s:
            kept.append("")
            continue
        if s.startswith("要点：") or s.startswith("时长："):
            continue
        s = re.sub(r"^\[[^\]]*\]\s*", "", s)
        if s:
            kept.append(s)
    return "\n".join(kept).strip()


def _load_notes_from_dir(notes_dir: Path) -> list[str] | None:
    """Load per-slide narrations from a notes/ directory (sorted, excluding total.md)."""
    if not notes_dir.exists():
        return None
    files = sorted(f for f in notes_dir.glob("*.md") if f.stem != "total")
    if not files:
        return None
    return [_clean_note(f.read_text(encoding="utf-8")) for f in files]


@router.post("/api/sessions/{session_id}/script", response_model=ScriptResponse)
async def generate_script(session_id: str) -> ScriptResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.script is not None:
        return ScriptResponse(script=session.script)

    # Try loading from notes/ directory in the PPT project
    if session.ppt_path:
        candidate_dirs = []
        if session.paths.notes_dir:
            candidate_dirs.append(Path(session.paths.notes_dir))
        ppt_path = Path(session.ppt_path)
        candidate_dirs.extend([ppt_path.parent / "notes", ppt_path / "notes"])
        for notes_dir in candidate_dirs:
            notes = _load_notes_from_dir(notes_dir)
            if notes:
                session_store.set_script(session_id, notes)
                return ScriptResponse(script=notes)

    # Fall back to LLM generation from PPTX
    if not session.ppt_path:
        raise HTTPException(status_code=400, detail="PPT not ready")

    logger.info("Generating narrations via LLM for session %s", session_id)
    slide_texts = extract_slide_texts(session.ppt_path)
    narrations = await generate_narrations(slide_texts)
    session_store.set_script(session_id, narrations)
    return ScriptResponse(script=narrations)


@router.get("/api/sessions/{session_id}/script", response_model=ScriptResponse)
async def get_script(session_id: str) -> ScriptResponse:
    session = session_store.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    if session.script is None:
        raise HTTPException(status_code=404, detail="Script not yet generated")
    return ScriptResponse(script=session.script)

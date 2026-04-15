from __future__ import annotations

import uuid
from typing import Dict, Optional

from app.models import ProgressState, SessionState, SessionStatus

# Valid status transitions
_TRANSITIONS: Dict[SessionStatus, set] = {
    SessionStatus.pending: {SessionStatus.processing},
    SessionStatus.processing: {SessionStatus.ready, SessionStatus.error},
    SessionStatus.ready: set(),
    SessionStatus.error: set(),
}

_sessions: Dict[str, SessionState] = {}


def create_session(pdf_path: str) -> SessionState:
    session_id = str(uuid.uuid4())
    session = SessionState(session_id=session_id, pdf_path=pdf_path)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Optional[SessionState]:
    return _sessions.get(session_id)


def update_status(session_id: str, new_status: SessionStatus, error: Optional[str] = None) -> SessionState:
    session = _sessions[session_id]
    allowed = _TRANSITIONS.get(session.status, set())
    if new_status not in allowed:
        raise ValueError(
            f"Invalid status transition: {session.status} -> {new_status} for session {session_id}"
        )
    session.status = new_status
    if error is not None:
        session.error = error
    return session


def update_progress(
    session_id: str,
    task: str,
    step: str,
    pct: int,
) -> SessionState:
    session = _sessions[session_id]
    if task == "ppt":
        session.progress.ppt_step = step
        session.progress.ppt_pct = pct
    elif task == "rag":
        session.progress.rag_step = step
        session.progress.rag_pct = pct
    return session


def set_script(session_id: str, script: list[str]) -> SessionState:
    session = _sessions[session_id]
    session.script = script
    return session


def set_output_paths(session_id: str, ppt_path: str = None, rag_index_path: str = None) -> SessionState:
    session = _sessions[session_id]
    if ppt_path is not None:
        session.ppt_path = ppt_path
    if rag_index_path is not None:
        session.rag_index_path = rag_index_path
    return session

from __future__ import annotations

import uuid
from typing import Dict, Optional

from app.models import LogEvent, ProgressState, SessionError, SessionFile, SessionPaths, SessionState, SessionStatus

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


def update_stage(
    session_id: str,
    task: str,
    stage: str,
    stage_label: str,
    pct: int,
    status: str = "running",
) -> SessionState:
    session = _sessions[session_id]
    target = session.stages.ppt if task == "ppt" else session.stages.rag
    target.stage = stage
    target.stage_label = stage_label
    target.pct = pct
    target.status = status
    update_progress(session_id, task, stage_label, pct)
    return session


def append_log(session_id: str, event: LogEvent) -> SessionState:
    session = _sessions[session_id]
    session.recent_logs.append(event)
    if len(session.recent_logs) > 200:
        session.recent_logs = session.recent_logs[-200:]
    return session


def set_script(session_id: str, script: list[str]) -> SessionState:
    session = _sessions[session_id]
    session.script = script
    return session


def set_output_paths(session_id: str, ppt_path: str = None, rag_index_path: str = None) -> SessionState:
    session = _sessions[session_id]
    if ppt_path is not None:
        session.ppt_path = ppt_path
        session.paths.ppt_path = ppt_path
    if rag_index_path is not None:
        session.rag_index_path = rag_index_path
        session.paths.rag_index_path = rag_index_path
    return session


def set_pdf_path(session_id: str, pdf_path: str) -> SessionState:
    session = _sessions[session_id]
    session.pdf_path = pdf_path
    session.paths.pdf_path = pdf_path
    return session


def set_ppt_config(session_id: str, config) -> SessionState:
    session = _sessions[session_id]
    session.ppt_config = config
    return session


def set_input_files(session_id: str, files: list[SessionFile]) -> SessionState:
    session = _sessions[session_id]
    session.input_files = files
    return session


def set_paths(session_id: str, paths: SessionPaths) -> SessionState:
    session = _sessions[session_id]
    session.paths = paths
    if paths.pdf_path:
        session.pdf_path = paths.pdf_path
    if paths.ppt_path:
        session.ppt_path = paths.ppt_path
    if paths.rag_index_path:
        session.rag_index_path = paths.rag_index_path
    return session


def update_path_fields(
    session_id: str,
    *,
    project_dir: str | None = None,
    ppt_path: str | None = None,
    slides_dir: str | None = None,
    notes_dir: str | None = None,
    rag_index_path: str | None = None,
) -> SessionState:
    session = _sessions[session_id]
    if project_dir is not None:
        session.paths.project_dir = project_dir
    if ppt_path is not None:
        session.ppt_path = ppt_path
        session.paths.ppt_path = ppt_path
    if slides_dir is not None:
        session.paths.slides_dir = slides_dir
    if notes_dir is not None:
        session.paths.notes_dir = notes_dir
    if rag_index_path is not None:
        session.rag_index_path = rag_index_path
        session.paths.rag_index_path = rag_index_path
    return session


def set_error_detail(session_id: str, error_detail: SessionError) -> SessionState:
    session = _sessions[session_id]
    session.error_detail = error_detail
    session.error = error_detail.message
    return session

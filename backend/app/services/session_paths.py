from __future__ import annotations

from pathlib import Path

from app.core.config import settings


def get_session_dir(session_id: str) -> Path:
    return settings.sessions_path / session_id


def get_session_input_dir(session_id: str) -> Path:
    path = get_session_dir(session_id) / "input"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_session_output_dir(session_id: str) -> Path:
    path = get_session_dir(session_id) / "output"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_session_logs_dir(session_id: str) -> Path:
    path = get_session_dir(session_id) / "logs"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_ppt_cache_dir(cache_key: str) -> Path:
    path = settings.ppt_cache_path / cache_key
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_rag_cache_dir(cache_key: str) -> Path:
    path = settings.rag_cache_path / cache_key
    path.mkdir(parents=True, exist_ok=True)
    return path

"""Space store：以 (pdf_hash, config_hash) 为 ID 的永久知识空间元数据。

每个 space 对应一份 PPT/RAG 产物 + 一份 PDF 文件。跨用户共享，对话历史按 user_id 分。
"""
from __future__ import annotations

import json
import logging
import threading
import time
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.models import PptConfig, SessionSourceDoc

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()

_REPO_ROOT = settings.project_root


def _to_repo_relative(value: str | None) -> str:
    """把绝对路径转成相对 REPO_ROOT 的 POSIX 风格路径，用于跨机器共享 space.json。"""
    if not value:
        return value or ""
    p = Path(value)
    if not p.is_absolute():
        return p.as_posix()
    try:
        return p.resolve().relative_to(_REPO_ROOT.resolve()).as_posix()
    except (ValueError, OSError):
        # 路径不在 repo 下（极少见，比如挂载盘）：原样保留绝对，至少不破坏数据
        return p.as_posix()


def _normalize_source_doc(doc: SessionSourceDoc | dict[str, Any]) -> dict[str, Any]:
    """把 SessionSourceDoc 序列化成 dict，并把里面的绝对路径字段转相对。"""
    raw = doc.model_dump() if isinstance(doc, SessionSourceDoc) else dict(doc)
    if raw.get("pdf_path"):
        raw["pdf_path"] = _to_repo_relative(raw["pdf_path"])
    if raw.get("markdown_path"):
        raw["markdown_path"] = _to_repo_relative(raw["markdown_path"])
    return raw


def _space_file(space_id: str) -> Path:
    return settings.spaces_path / f"{space_id}.json"


def _ensure_dir() -> None:
    settings.spaces_path.mkdir(parents=True, exist_ok=True)


def _load(space_id: str) -> dict[str, Any] | None:
    path = _space_file(space_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read space %s", space_id)
        return None


def _save(space_id: str, data: dict[str, Any]) -> None:
    _ensure_dir()
    path = _space_file(space_id)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get(space_id: str) -> dict[str, Any] | None:
    with _LOCK:
        return _load(space_id)


def upsert(
    space_id: str,
    *,
    user_id: str,
    pdf_filename: str,
    pdf_path: str,
    pdf_hash: str,
    config: PptConfig,
    paper_title: str | None = None,
    session_type: str = "single",
    source_documents: list[SessionSourceDoc] | None = None,
) -> dict[str, Any]:
    """创建或更新空间元数据。已有空间会把 user_id 加入 contributors。"""
    with _LOCK:
        existing = _load(space_id) or {}
        contributors = set(existing.get("contributors") or [])
        contributors.add(user_id)
        now = time.time()
        # 已存在的空间保留旧 state，新空间默认 pending；如旧空间是 failed，新一次上传会被视为重试 → 重置到 pending
        prior_state = existing.get("state")
        new_state = "pending" if prior_state in (None, "failed") else prior_state
        data = {
            "space_id": space_id,
            "pdf_filename": pdf_filename,
            "pdf_path": _to_repo_relative(pdf_path),
            "pdf_hash": pdf_hash,
            "config": config.model_dump(),
            "paper_title": paper_title or existing.get("paper_title") or pdf_filename,
            "session_type": session_type,
            "source_documents": [_normalize_source_doc(doc) for doc in (source_documents or [])],
            "contributors": sorted(contributors),
            "state": new_state,
            "error_message": existing.get("error_message") if new_state != "pending" else None,
            "created_at": existing.get("created_at") or now,
            "updated_at": now,
            "last_accessed_by": {
                **(existing.get("last_accessed_by") or {}),
                user_id: now,
            },
        }
        _save(space_id, data)
        return data


def mark_state(space_id: str, state: str, *, error_message: str | None = None) -> None:
    """更新 space 的处理状态。state ∈ {pending, ready, failed}。"""
    with _LOCK:
        data = _load(space_id)
        if not data:
            return
        data["state"] = state
        data["error_message"] = error_message
        data["updated_at"] = time.time()
        _save(space_id, data)


def delete_space(space_id: str) -> bool:
    """删除 space 元数据（不删 PPT/RAG 缓存目录，那些跨 space_id 共享）。"""
    with _LOCK:
        path = _space_file(space_id)
        if not path.exists():
            return False
        path.unlink()
        return True


def touch_access(space_id: str, user_id: str) -> None:
    """记录用户最近一次访问该空间的时间。"""
    with _LOCK:
        data = _load(space_id)
        if not data:
            return
        contributors = set(data.get("contributors") or [])
        contributors.add(user_id)
        data["contributors"] = sorted(contributors)
        last_access = dict(data.get("last_accessed_by") or {})
        last_access[user_id] = time.time()
        data["last_accessed_by"] = last_access
        data["updated_at"] = time.time()
        _save(space_id, data)


def list_for_user(user_id: str) -> list[dict[str, Any]]:
    """按 user 最近访问时间倒序列出所有空间。"""
    _ensure_dir()
    items: list[dict[str, Any]] = []
    for path in settings.spaces_path.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if user_id not in (data.get("contributors") or []):
            continue
        last_access = (data.get("last_accessed_by") or {}).get(user_id) or data.get("updated_at") or 0
        items.append({**data, "_last_access_for_user": last_access})
    items.sort(key=lambda x: x.get("_last_access_for_user", 0), reverse=True)
    for item in items:
        item.pop("_last_access_for_user", None)
    return items

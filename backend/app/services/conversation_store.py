"""Conversation store：按 (user_id, space_id) 分目录持久化对话。"""
from __future__ import annotations

import json
import logging
import re
import threading
import time
import uuid
from pathlib import Path
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)

_LOCK = threading.RLock()
_MAX_CONVERSATIONS_PER_SPACE = 50
_INVALID_ID_REGEX = re.compile(r"[^A-Za-z0-9_\-.]")


def _safe_id(value: str) -> str:
    """避免 user_id / space_id 含路径分隔符。"""
    sanitized = _INVALID_ID_REGEX.sub("_", value.strip()) if value else ""
    return sanitized[:64] or "anonymous"


def _user_space_dir(user_id: str, space_id: str) -> Path:
    return settings.conversations_path / _safe_id(user_id) / _safe_id(space_id)


def _index_file(user_id: str, space_id: str) -> Path:
    return _user_space_dir(user_id, space_id) / "index.json"


def _conv_file(user_id: str, space_id: str, conv_id: str) -> Path:
    return _user_space_dir(user_id, space_id) / f"{_safe_id(conv_id)}.json"


def _read_index(user_id: str, space_id: str) -> list[dict[str, Any]]:
    path = _index_file(user_id, space_id)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to parse conversation index: %s", path)
        return []


def _write_index(user_id: str, space_id: str, items: list[dict[str, Any]]) -> None:
    dir_path = _user_space_dir(user_id, space_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    _index_file(user_id, space_id).write_text(
        json.dumps(items, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _read_conv(user_id: str, space_id: str, conv_id: str) -> dict[str, Any] | None:
    path = _conv_file(user_id, space_id, conv_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        logger.warning("Failed to read conversation: %s", path)
        return None


def _write_conv(user_id: str, space_id: str, conv: dict[str, Any]) -> None:
    dir_path = _user_space_dir(user_id, space_id)
    dir_path.mkdir(parents=True, exist_ok=True)
    _conv_file(user_id, space_id, conv["id"]).write_text(
        json.dumps(conv, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _refresh_index_entry(user_id: str, space_id: str, conv: dict[str, Any]) -> None:
    items = _read_index(user_id, space_id)
    items = [item for item in items if item.get("id") != conv["id"]]
    items.append({
        "id": conv["id"],
        "title": conv.get("title") or "新会话",
        "msg_count": len(conv.get("messages") or []),
        "created_at": conv.get("created_at"),
        "updated_at": conv.get("updated_at"),
    })
    items.sort(key=lambda x: x.get("updated_at") or 0, reverse=True)
    _write_index(user_id, space_id, items)


def list_conversations(user_id: str, space_id: str) -> list[dict[str, Any]]:
    with _LOCK:
        return _read_index(user_id, space_id)


def get_conversation(user_id: str, space_id: str, conv_id: str) -> dict[str, Any] | None:
    with _LOCK:
        return _read_conv(user_id, space_id, conv_id)


def create_conversation(
    user_id: str,
    space_id: str,
    *,
    title: str | None = None,
) -> dict[str, Any]:
    with _LOCK:
        items = _read_index(user_id, space_id)
        if len(items) >= _MAX_CONVERSATIONS_PER_SPACE:
            raise ValueError(
                f"已达到上限（{_MAX_CONVERSATIONS_PER_SPACE} 个会话），请先删除旧会话再新建。"
            )
        now = time.time()
        conv = {
            "id": uuid.uuid4().hex,
            "title": title or "新会话",
            "messages": [],
            "created_at": now,
            "updated_at": now,
        }
        _write_conv(user_id, space_id, conv)
        _refresh_index_entry(user_id, space_id, conv)
        return conv


def append_message(
    user_id: str,
    space_id: str,
    conv_id: str,
    *,
    role: str,
    content: str,
    sources: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    with _LOCK:
        conv = _read_conv(user_id, space_id, conv_id)
        if conv is None:
            raise KeyError(f"conversation not found: {conv_id}")
        message = {
            "role": role,
            "content": content,
            "ts": time.time(),
        }
        if sources is not None:
            message["sources"] = sources
        conv.setdefault("messages", []).append(message)
        conv["updated_at"] = time.time()
        _write_conv(user_id, space_id, conv)
        _refresh_index_entry(user_id, space_id, conv)
        return conv


def rename(user_id: str, space_id: str, conv_id: str, title: str) -> dict[str, Any]:
    with _LOCK:
        conv = _read_conv(user_id, space_id, conv_id)
        if conv is None:
            raise KeyError(f"conversation not found: {conv_id}")
        conv["title"] = title.strip()[:60] or conv.get("title") or "新会话"
        conv["updated_at"] = time.time()
        _write_conv(user_id, space_id, conv)
        _refresh_index_entry(user_id, space_id, conv)
        return conv


def delete_conversation(user_id: str, space_id: str, conv_id: str) -> bool:
    with _LOCK:
        conv_path = _conv_file(user_id, space_id, conv_id)
        existed = conv_path.exists()
        if existed:
            conv_path.unlink()
        items = [item for item in _read_index(user_id, space_id) if item.get("id") != conv_id]
        _write_index(user_id, space_id, items)
        return existed


def latest_conversation_id(user_id: str, space_id: str) -> str | None:
    items = list_conversations(user_id, space_id)
    return items[0]["id"] if items else None

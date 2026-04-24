from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.models import LogEvent
from app.services import session_store
from app.services.connection_manager import manager as ws_manager
from app.services.session_paths import get_session_logs_dir

logger = logging.getLogger(__name__)


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SessionLogRecorder:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.logs_dir = get_session_logs_dir(session_id)
        self.log_file = self.logs_dir / "generation.jsonl"

    async def record(
        self,
        *,
        source: str,
        level: str,
        stage: str,
        message: str,
        details: dict[str, Any] | None = None,
        broadcast: bool = True,
    ) -> LogEvent:
        event = LogEvent(
            ts=_iso_now(),
            source=source,
            level=level,
            stage=stage,
            message=message,
            details=details,
        )
        self._append_to_file(event)
        session_store.append_log(self.session_id, event)
        if broadcast:
            try:
                await ws_manager.broadcast(self.session_id, {"event": "log", **event.model_dump(mode="json")})
            except Exception:
                logger.exception("Failed to broadcast log event for session %s", self.session_id)
        return event

    def _append_to_file(self, event: LogEvent) -> None:
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        with self.log_file.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event.model_dump(mode="json"), ensure_ascii=False) + "\n")


def load_session_logs(session_id: str, limit: int = 200) -> list[dict[str, Any]]:
    log_file = get_session_logs_dir(session_id) / "generation.jsonl"
    if not log_file.exists():
        return []

    lines = log_file.read_text(encoding="utf-8").splitlines()
    selected = lines[-limit:] if limit > 0 else lines
    logs: list[dict[str, Any]] = []
    for line in selected:
        if not line.strip():
            continue
        try:
            logs.append(json.loads(line))
        except json.JSONDecodeError:
            logger.warning("Skipping malformed session log line for %s", session_id)
    return logs

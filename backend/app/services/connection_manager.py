from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Dict, List

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: Dict[str, List[WebSocket]] = defaultdict(list)

    async def connect(self, session_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections[session_id].append(websocket)

    def disconnect(self, session_id: str, websocket: WebSocket) -> None:
        conns = self._connections.get(session_id, [])
        if websocket in conns:
            conns.remove(websocket)

    async def broadcast(self, session_id: str, message: dict) -> None:
        conns = list(self._connections.get(session_id, []))
        if not conns:
            return
        dead: List[WebSocket] = []
        results = await asyncio.gather(
            *(ws.send_json(message) for ws in conns),
            return_exceptions=True,
        )
        for ws, result in zip(conns, results):
            if isinstance(result, Exception):
                dead.append(ws)
        for ws in dead:
            self.disconnect(session_id, ws)


manager = ConnectionManager()

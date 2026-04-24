from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services import session_store
from app.services.connection_manager import manager

router = APIRouter()


@router.websocket("/ws/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str) -> None:
    session = session_store.get_session(session_id)
    if session is None:
        await websocket.accept()
        await websocket.send_json({"error": "session not found", "terminal": True})
        await websocket.close()
        return

    await manager.connect(session_id, websocket)
    await websocket.send_json(session.model_dump(mode="json"))

    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(session_id, websocket)

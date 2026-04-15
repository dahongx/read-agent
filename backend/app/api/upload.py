from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.core.config import settings
from app.models import PptConfig, SessionStatus, UploadResponse
from app.services import session_store, task_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile,
    ppt_config: str = Form(default="{}"),
) -> UploadResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    first_chunk = await file.read(1)
    if not first_chunk:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    config_payload = (ppt_config or "").strip()
    if not config_payload or config_payload == "{}":
        config = PptConfig()
    else:
        try:
            raw_config = json.loads(config_payload)
            if not isinstance(raw_config, dict):
                raise HTTPException(status_code=400, detail="ppt_config must be a JSON object")
            config = PptConfig(**raw_config)
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid ppt_config JSON: {exc.msg}") from exc
        except ValidationError as exc:
            raise HTTPException(status_code=400, detail=exc.errors()) from exc

    session = session_store.create_session(pdf_path="")
    session_store._sessions[session.session_id].ppt_config = config

    upload_dir = settings.upload_path / session.session_id
    upload_dir.mkdir(parents=True, exist_ok=True)
    dest = upload_dir / filename

    async with aiofiles.open(dest, "wb") as f:
        await f.write(first_chunk)
        while chunk := await file.read(1024 * 64):
            await f.write(chunk)

    session_store._sessions[session.session_id].pdf_path = str(dest)
    logger.info(
        "[UPLOAD] session=%s  file=%s  size=%s bytes  config=%s",
        session.session_id, dest, dest.stat().st_size, config.model_dump(),
    )

    asyncio.create_task(task_manager.run_tasks(session.session_id, str(dest), config))
    logger.info("[UPLOAD] Background task created for session=%s", session.session_id)

    return UploadResponse(session_id=session.session_id, status=SessionStatus.pending)

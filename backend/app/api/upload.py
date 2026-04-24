from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.models import PptConfig, SessionFile, SessionPaths, SessionStatus, UploadResponse
from app.services import session_store, task_manager
from app.services.session_paths import (
    get_session_dir,
    get_session_input_dir,
    get_session_logs_dir,
    get_session_output_dir,
)

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
    session_store.set_ppt_config(session.session_id, config)

    session_dir = get_session_dir(session.session_id)
    input_dir = get_session_input_dir(session.session_id)
    output_dir = get_session_output_dir(session.session_id)
    logs_dir = get_session_logs_dir(session.session_id)
    dest = input_dir / filename

    async with aiofiles.open(dest, "wb") as f:
        await f.write(first_chunk)
        while chunk := await file.read(1024 * 64):
            await f.write(chunk)

    file_size = dest.stat().st_size
    session_store.set_paths(
        session.session_id,
        SessionPaths(
            session_dir=str(session_dir),
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            logs_dir=str(logs_dir),
            pdf_path=str(dest),
        ),
    )
    session_store.set_pdf_path(session.session_id, str(dest))
    session_store.set_input_files(
        session.session_id,
        [SessionFile(filename=filename, path=str(dest), size=file_size)],
    )
    logger.info(
        "[UPLOAD] session=%s  file=%s  size=%s bytes  config=%s",
        session.session_id, dest, file_size, config.model_dump(),
    )

    asyncio.create_task(task_manager.run_tasks(session.session_id, str(dest), config))
    logger.info("[UPLOAD] Background task created for session=%s", session.session_id)

    return UploadResponse(session_id=session.session_id, status=SessionStatus.pending)

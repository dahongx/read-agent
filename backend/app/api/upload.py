from __future__ import annotations

import asyncio
import hashlib
import json
import logging
from pathlib import Path

import aiofiles
from fastapi import APIRouter, Form, HTTPException, UploadFile
from pydantic import ValidationError

from app.models import (
    PptConfig,
    SessionFile,
    SessionPaths,
    SessionSourceDoc,
    SessionStatus,
    UploadResponse,
)
from app.services import session_store, space_store, task_manager
from app.services.ppt_generator import compute_cache_key, compute_multi_cache_key
from app.services.session_paths import (
    get_session_dir,
    get_session_input_dir,
    get_session_logs_dir,
    get_session_output_dir,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def _parse_ppt_config(ppt_config: str) -> PptConfig:
    config_payload = (ppt_config or "").strip()
    if not config_payload or config_payload == "{}":
        return PptConfig()

    try:
        raw_config = json.loads(config_payload)
        if not isinstance(raw_config, dict):
            raise HTTPException(status_code=400, detail="ppt_config must be a JSON object")
        return PptConfig(**raw_config)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid ppt_config JSON: {exc.msg}") from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=exc.errors()) from exc


def _normalize_user_id(user_id: str | None) -> str:
    return (user_id or "anonymous").strip() or "anonymous"


async def _save_upload_file(upload: UploadFile, dest: Path) -> tuple[int, str]:
    first_chunk = await upload.read(1)
    if not first_chunk:
        raise HTTPException(status_code=400, detail=f"Uploaded file is empty: {upload.filename or dest.name}")

    digest = hashlib.sha256()
    digest.update(first_chunk)
    size = len(first_chunk)

    async with aiofiles.open(dest, "wb") as f:
        await f.write(first_chunk)
        while chunk := await upload.read(1024 * 64):
            size += len(chunk)
            digest.update(chunk)
            await f.write(chunk)

    return size, digest.hexdigest()


@router.post("/api/upload", response_model=UploadResponse)
async def upload_pdf(
    file: UploadFile,
    ppt_config: str = Form(default="{}"),
    user_id: str = Form(default="anonymous"),
) -> UploadResponse:
    filename = file.filename or ""
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted")

    user_id = _normalize_user_id(user_id)
    config = _parse_ppt_config(ppt_config)

    session = session_store.create_session(pdf_path="", user_id=user_id)
    session_store.set_ppt_config(session.session_id, config)

    session_dir = get_session_dir(session.session_id)
    input_dir = get_session_input_dir(session.session_id)
    output_dir = get_session_output_dir(session.session_id)
    logs_dir = get_session_logs_dir(session.session_id)
    dest = input_dir / filename

    file_size, content_hash = await _save_upload_file(file, dest)

    # space_id 复用 PPT 缓存的 cache_key，保证产物路径直接通过 space_id 查得到
    space_id = compute_cache_key(str(dest), config)
    pdf_hash = content_hash[:16]
    session_store.set_user_and_space(session.session_id, user_id, space_id)

    space_store.upsert(
        space_id,
        user_id=user_id,
        pdf_filename=filename,
        pdf_path=str(dest),
        pdf_hash=pdf_hash,
        config=config,
        paper_title=Path(filename).stem,
        session_type="single",
    )

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
        "[UPLOAD] session=%s user=%s space=%s file=%s size=%s config=%s",
        session.session_id, user_id, space_id, dest, file_size, config.model_dump(),
    )

    asyncio.create_task(task_manager.run_tasks(session.session_id, str(dest), config))

    return UploadResponse(
        session_id=session.session_id,
        status=SessionStatus.pending,
        space_id=space_id,
        cache_hit=False,
    )


@router.post("/api/upload-multi", response_model=UploadResponse)
async def upload_multi_pdf(
    files: list[UploadFile],
    ppt_config: str = Form(default="{}"),
    user_id: str = Form(default="anonymous"),
) -> UploadResponse:
    if len(files) < 2:
        raise HTTPException(status_code=400, detail="At least 2 PDF files are required")

    user_id = _normalize_user_id(user_id)
    config = _parse_ppt_config(ppt_config)

    invalid_files = [f.filename or "" for f in files if not (f.filename or "").lower().endswith(".pdf")]
    if invalid_files:
        raise HTTPException(status_code=400, detail=f"Only PDF files are accepted: {', '.join(invalid_files)}")

    session = session_store.create_session(pdf_path="", session_type="multi", user_id=user_id)
    session_store.set_ppt_config(session.session_id, config)
    session_store.set_session_type(session.session_id, "multi")

    session_dir = get_session_dir(session.session_id)
    input_dir = get_session_input_dir(session.session_id)
    output_dir = get_session_output_dir(session.session_id)
    logs_dir = get_session_logs_dir(session.session_id)

    input_files: list[SessionFile] = []
    source_documents: list[SessionSourceDoc] = []
    pdf_paths: list[str] = []

    for idx, upload in enumerate(files, start=1):
        filename = upload.filename or f"paper_{idx}.pdf"
        safe_name = Path(filename).name or f"paper_{idx}.pdf"
        dest = input_dir / safe_name
        if dest.exists():
            dest = input_dir / f"{dest.stem}_{idx}{dest.suffix}"

        file_size, content_hash = await _save_upload_file(upload, dest)
        input_files.append(SessionFile(filename=safe_name, path=str(dest), size=file_size))
        source_documents.append(
            SessionSourceDoc(
                doc_id=f"doc_{idx:03d}",
                order=idx,
                source_file_name=safe_name,
                pdf_path=str(dest),
                content_hash=content_hash,
            )
        )
        pdf_paths.append(str(dest))

    space_id = compute_multi_cache_key(pdf_paths, config)
    session_store.set_user_and_space(session.session_id, user_id, space_id)

    space_store.upsert(
        space_id,
        user_id=user_id,
        pdf_filename=", ".join(f.filename for f in input_files),
        pdf_path="",
        pdf_hash="multi",
        config=config,
        paper_title=f"多篇综述 ({len(input_files)})",
        session_type="multi",
        source_documents=source_documents,
    )

    session_store.set_paths(
        session.session_id,
        SessionPaths(
            session_dir=str(session_dir),
            input_dir=str(input_dir),
            output_dir=str(output_dir),
            logs_dir=str(logs_dir),
        ),
    )
    session_store.set_input_files(session.session_id, input_files)
    session_store.set_source_documents(session.session_id, source_documents)

    logger.info(
        "[UPLOAD_MULTI] session=%s user=%s space=%s files=%d config=%s",
        session.session_id, user_id, space_id, len(input_files), config.model_dump(),
    )

    asyncio.create_task(task_manager.run_multi_tasks(session.session_id, pdf_paths, config))

    return UploadResponse(
        session_id=session.session_id,
        status=SessionStatus.pending,
        space_id=space_id,
        cache_hit=False,
    )

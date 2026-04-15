## 1. Project Setup

- [x] 1.1 Create `backend/` directory structure (`app/api/`, `app/core/`, `app/services/`)
- [x] 1.2 Create `backend/requirements.txt` with dependencies (fastapi, uvicorn, python-multipart, python-dotenv, aiofiles)
- [x] 1.3 Create `backend/.env.example` with `DEV_MODE=false` and other config placeholders

## 2. Models

- [x] 2.1 Create `backend/app/models.py` with Pydantic models: `SessionStatus` enum, `ProgressState`, `SessionState`, `UploadResponse`

## 3. Core Config & Session Store

- [x] 3.1 Create `backend/app/core/config.py` — load `.env`, expose `Settings` (DEV_MODE, fixture path, upload dir)
- [x] 3.2 Create `backend/app/services/session_store.py` — in-memory dict, `create_session`, `get_session`, `update_status`, `update_progress` with transition validation

## 4. WebSocket Connection Manager

- [x] 4.1 Create `backend/app/services/connection_manager.py` — `ConnectionManager` class with `connect`, `disconnect`, `broadcast` methods

## 5. DEV_MODE & Task Manager

- [x] 5.1 Create `backend/app/services/dev_mode.py` — `validate_fixture()` checks required files exist; raises `FixtureIncompleteError` listing missing files
- [x] 5.2 Create `backend/app/services/task_manager.py` — `run_tasks(session_id, pdf_path)` launches ppt_task and rag_task concurrently with `asyncio.create_task`; stub implementations that emit progress events and complete successfully

## 6. API Routes

- [x] 6.1 Create `backend/app/api/upload.py` — `POST /api/upload`: validate PDF, save to temp dir, create session, launch task_manager, return `UploadResponse`
- [x] 6.2 Create `backend/app/api/sessions.py` — `GET /api/sessions/{session_id}`: return session state or 404
- [x] 6.3 Create `backend/app/api/ws.py` — `WebSocket /ws/{session_id}`: accept, send current state, keep open for broadcast

## 7. App Entry Point

- [x] 7.1 Create `backend/app/core/startup.py` — on startup: if DEV_MODE, call `validate_fixture()` and fail fast if incomplete
- [x] 7.2 Create `backend/main.py` — create FastAPI app, include routers, attach startup event, mount connection manager on `app.state`

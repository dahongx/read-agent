import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import chat, script, sessions, upload, ws
from app.core.startup import lifespan

logging.basicConfig(level=logging.INFO)

app = FastAPI(title="文献阅读 Agent API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(sessions.router)
app.include_router(ws.router)
app.include_router(chat.router)
app.include_router(script.router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}


# Serve frontend build if it exists (production / sharing mode)
_dist = Path(__file__).parent.parent / "frontend" / "dist"
if _dist.exists():
    from fastapi.responses import FileResponse

    app.mount("/assets", StaticFiles(directory=str(_dist / "assets")), name="assets")

    _pdfjs = _dist / "pdfjs"
    if _pdfjs.exists():
        app.mount("/pdfjs", StaticFiles(directory=str(_pdfjs)), name="pdfjs")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def serve_spa(full_path: str):
        return FileResponse(str(_dist / "index.html"))

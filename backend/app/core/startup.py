import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.config import settings

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.upload_path.mkdir(parents=True, exist_ok=True)
    settings.ppt_cache_path.mkdir(parents=True, exist_ok=True)
    logger.info("Upload dir: %s", settings.upload_path)
    logger.info("PPT cache dir: %s", settings.ppt_cache_path)
    logger.info("Skill dir: %s", settings.skill_path)
    yield

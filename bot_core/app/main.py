from __future__ import annotations

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI

from app.api import admin, health, inbound, knowledge
from app.config import settings
from app.db import engine, ping_database
from app.services.logging_service import configure_logging, log_event


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    settings.validate_runtime()
    if settings.startup_validate_db:
        await ping_database()
    log_event(logger, logging.INFO, "app_startup", environment=settings.environment, ai_enabled=settings.ai_enabled)
    try:
        yield
    finally:
        await engine.dispose()
        log_event(logger, logging.INFO, "app_shutdown")


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(inbound.router)
app.include_router(admin.router)
app.include_router(knowledge.router)

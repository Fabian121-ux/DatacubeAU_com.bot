from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from app.api import admin, admin_auth, admin_ui, health, inbound, knowledge
from app.config import settings
from app.db import engine, ping_database
from app.services.admin_auth_service import AdminAuthService
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

@app.get("/", include_in_schema=False)
async def root(request: Request) -> RedirectResponse:
    auth_service = AdminAuthService()
    if auth_service.get_soft_session(request):
        return RedirectResponse(url="/admin/ui", status_code=302)
    return RedirectResponse(url="/admin/login", status_code=302)

app.include_router(health.router)
app.include_router(inbound.router)
app.include_router(admin_auth.router)
app.include_router(admin.router)
app.include_router(knowledge.router)
app.include_router(admin_ui.router)

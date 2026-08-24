from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager, suppress
import logging
from pathlib import Path

from fastapi import FastAPI

from app.api import admin, admin_auth, admin_ui, conversation_takeover_admin, health, inbound, knowledge
from app.config import settings
from app.db import SessionLocal, engine, ping_database
from app.services.bot_config_service import BotConfigService
from app.services.faq_service import FAQService
from app.services.identity_registry_service import IdentityRegistryService
from app.services.logging_service import configure_logging, log_event
from app.workers.background_workers import (
    conversation_open_loop_worker,
    conversation_takeover_worker,
    outbound_queue_delivery_worker,
    waha_monitor_worker,
)


configure_logging()
logger = logging.getLogger(__name__)
CORE_FAQ_PATH = Path(__file__).resolve().parents[1] / "core_faq.md"


@asynccontextmanager
async def lifespan(_: FastAPI):
    tasks: list[asyncio.Task[None]] = []
    settings.validate_runtime()
    if settings.startup_validate_db:
        await ping_database()
    await _sync_core_faq()
    tasks.append(asyncio.create_task(outbound_queue_delivery_worker(), name="outbound-queue-delivery"))
    tasks.append(asyncio.create_task(conversation_takeover_worker(), name="conversation-takeover"))
    tasks.append(asyncio.create_task(conversation_open_loop_worker(), name="conversation-open-loops"))
    tasks.append(asyncio.create_task(waha_monitor_worker(), name="waha-monitor"))
    log_event(logger, logging.INFO, "app_startup", environment=settings.environment, ai_enabled=settings.ai_enabled)
    try:
        yield
    finally:
        for task in tasks:
            task.cancel()
        for task in tasks:
            with suppress(asyncio.CancelledError):
                await task
        await engine.dispose()
        log_event(logger, logging.INFO, "app_shutdown")


async def _sync_core_faq() -> None:
    async with SessionLocal() as session:
        config = BotConfigService(session)
        await IdentityRegistryService(session).ensure_defaults_from_profile(await config.get_identity_profile())
        service = FAQService(session)
        count = await service.load_faq_from_file(str(CORE_FAQ_PATH))
        await session.commit()
        log_event(logger, logging.INFO, "core_faq_synced", path=str(CORE_FAQ_PATH), entries=count)


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(health.router)
app.include_router(inbound.router)
app.include_router(admin_auth.router)
app.include_router(admin.router)
app.include_router(conversation_takeover_admin.router)
app.include_router(knowledge.router)
app.include_router(admin_ui.router)

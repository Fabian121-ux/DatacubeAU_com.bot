from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.router import InboundRouter
from app.db import get_db_session
from app.services.logging_service import log_event


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/waha")
async def waha_webhook(event: dict[str, Any], db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    inbound_router = InboundRouter(db)
    try:
        return await inbound_router.process_event(event)
    except Exception as exc:  # noqa: BLE001
        await db.rollback()
        log_event(logger, logging.ERROR, "webhook_processing_failed", error=str(exc))
        logger.exception("WAHA inbound processing failed")
        raise HTTPException(status_code=500, detail="inbound processing failed") from exc
    finally:
        await inbound_router.close()

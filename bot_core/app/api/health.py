from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db_session
from app.services.waha_client import WAHAClient, WahaClientError


router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    db_status = "ok"
    waha_status: str | dict[str, object] = "unknown"
    try:
        await db.execute(text("SELECT 1"))
    except Exception:  # noqa: BLE001
        db_status = "error"
    client = WAHAClient()
    try:
        waha_status = await client.get_session_status()
    except WahaClientError as exc:
        waha_status = {"status": "error", "detail": str(exc)}
    finally:
        await client.close()
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "database": db_status,
        "waha": waha_status,
        "ai_enabled": settings.ai_enabled,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

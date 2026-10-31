from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db import get_db_session
from app.services.waha_client import WAHAClient, WahaClientError


router = APIRouter()


@router.get("/health")
async def health(db: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail={"database": "error", "error": str(exc)}) from exc
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.environment,
        "database": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/health/dependencies")
async def dependency_health(db: AsyncSession = Depends(get_db_session)) -> dict[str, object]:
    db_status: str | dict[str, object] = "ok"
    waha_status: str | dict[str, object] = "unknown"

    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        db_status = {"status": "error", "detail": str(exc)}

    client = WAHAClient()
    try:
        waha_status = await client.get_session_status()
    except WahaClientError as exc:
        waha_status = {"status": "error", "detail": str(exc)}
    finally:
        await client.close()

    openrouter_status: dict[str, object] = {
        "enabled": settings.ai_enabled,
        "configured": bool(settings.openrouter_api_key),
        "base_url": settings.openrouter_base_url if settings.ai_enabled else "",
    }

    return {
        "status": "ok" if db_status == "ok" and not _is_dependency_error(waha_status) else "degraded",
        "service": settings.app_name,
        "environment": settings.environment,
        "database": db_status,
        "waha": waha_status,
        "openrouter": openrouter_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def _is_dependency_error(value: str | dict[str, object]) -> bool:
    if isinstance(value, dict):
        return value.get("status") == "error"
    return False

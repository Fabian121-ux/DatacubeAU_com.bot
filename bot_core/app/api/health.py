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
    """Deprecated compatibility wrapper delegating to canonical status."""
    from app.services.system_status_service import SystemStatusService
    service = SystemStatusService(db)
    status = await service.build_canonical_status()
    
    db_status = status["database"]
    waha_status = status["waha"]
    ai_status = status["ai_provider"]
    
    return {
        "status": "ok" if db_status.get("status") == "ok" and waha_status.get("service_reachable") else "degraded",
        "service": status["api"]["service"],
        "environment": status["api"]["environment"],
        "database": db_status,
        "waha": waha_status,
        "openrouter": ai_status,
        "timestamp": status["timestamp"],
    }

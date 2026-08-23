from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.schema import FAQEntry
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.time import utcnow


class SystemStatusService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def build_canonical_status(self) -> dict[str, Any]:
        return {
            "api": self._get_api_status(),
            "database": await self._get_database_status(),
            "faq_bootstrap": await self._get_faq_bootstrap_status(),
            "waha": await self._get_waha_status(),
            "ai_provider": self._get_ai_status(),
            "workers": self._get_workers_status(),
            "timestamp": utcnow().isoformat(),
        }

    def _get_api_status(self) -> dict[str, Any]:
        return {
            "service": settings.app_name,
            "environment": settings.environment,
            "status": "healthy",
        }

    async def _get_database_status(self) -> dict[str, Any]:
        try:
            from sqlalchemy import text
            await self.session.execute(text("SELECT 1"))
            return {"status": "ok", "detail": None}
        except Exception as exc:
            return {"status": "error", "detail": str(exc)}

    async def _get_faq_bootstrap_status(self) -> dict[str, Any]:
        try:
            stmt = select(
                func.count().label("total"),
                func.max(FAQEntry.last_synchronized_at).label("last_sync")
            ).where(FAQEntry.source_id == "core_faq")
            
            result = (await self.session.execute(stmt)).one_or_none()
            if not result:
                return {"status": "unknown", "entries": 0, "last_synchronized_at": None}
            
            count, last_sync = result
            if count > 0 and last_sync:
                return {
                    "status": "completed",
                    "entries": count,
                    "last_synchronized_at": last_sync.isoformat() if last_sync else None
                }
            return {"status": "not_run", "entries": 0, "last_synchronized_at": None}
        except Exception as exc:
            return {"status": "failed", "entries": 0, "last_synchronized_at": None, "error": str(exc)}

    async def _get_waha_status(self) -> dict[str, Any]:
        client = WAHAClient()
        raw_payload = None
        error = None
        try:
            raw_payload = await client.get_session_status()
        except WahaClientError as exc:
            error = str(exc)
        except Exception as exc:
            error = str(exc)
        finally:
            await client.close()
            
        return WAHAClient.normalize_waha_status(raw_payload, error)

    def _get_ai_status(self) -> dict[str, Any]:
        if not settings.ai_enabled:
            return {
                "state": "disabled_by_setting",
                "enabled": False,
                "configured": bool(settings.openrouter_api_key),
                "missing_config": []
            }
        
        missing = []
        if not settings.openrouter_api_key:
            missing.append("OPENROUTER_API_KEY")
        if not settings.openrouter_model_light:
            missing.append("OPENROUTER_MODEL_LIGHT")
        if not settings.openrouter_model_deep:
            missing.append("OPENROUTER_MODEL_DEEP")
            
        if missing:
            return {
                "state": "disabled_by_configuration",
                "enabled": True,
                "configured": False,
                "missing_config": missing
            }
            
        return {
            "state": "enabled",
            "enabled": True,
            "configured": True,
            "missing_config": []
        }

    def _get_workers_status(self) -> dict[str, Any]:
        # Since workers do not emit reliable heartbeats, we return unknown.
        return {
            "outbound_worker": {"status": "unknown"},
            "waha_monitor": {"status": "unknown"}
        }

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.models.schema import AuditLog
from app.services.contact_intelligence_service import ContactIntelligenceService
from app.services.contact_sync_service import ContactSyncService


router = APIRouter(
    prefix="/admin/contact-intelligence",
    tags=["admin"],
    dependencies=[Depends(require_admin_session)],
)


@router.get("/resolve")
async def resolve_contact_reference(
    q: str = Query(min_length=1, max_length=180),
    limit: int = Query(default=5, ge=1, le=20),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Resolve an owner-supplied WhatsApp contact reference with explainable provenance."""
    result = await ContactIntelligenceService(db).resolve(q, limit=limit)
    match = result.get("match") or {}
    candidates = result.get("candidates") or []
    db.add(
        AuditLog(
            action="contact_resolution_checked",
            entity_type="contacts",
            entity_id=str(match.get("contact_id")) if match.get("contact_id") else None,
            details_json={
                "status": result.get("status"),
                "confidence": result.get("confidence"),
                "margin": result.get("margin"),
                "matched_field": match.get("matched_field"),
                "candidate_ids": [item.get("contact_id") for item in candidates[:5]],
            },
        )
    )
    await db.commit()
    return result


@router.post("/sync")
async def sync_whatsapp_contacts(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    """Pull saved WhatsApp contacts from WAHA into Zina's existing contacts table."""
    result = await ContactSyncService(db).sync()
    db.add(
        AuditLog(
            action="waha_contacts_synced",
            entity_type="contacts",
            entity_id=None,
            details_json=result,
        )
    )
    await db.commit()
    return {"ok": True, **result}

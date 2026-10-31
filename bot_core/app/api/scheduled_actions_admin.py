from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.services.scheduled_action_service import ScheduledActionService


router = APIRouter(
    prefix="/admin/scheduled-actions",
    tags=["admin"],
    dependencies=[Depends(require_admin_session)],
)


class ScheduledMessageIn(BaseModel):
    target: str = Field(min_length=1, max_length=180)
    text: str = Field(min_length=1, max_length=8000)
    scheduled_for: datetime
    timezone: str = Field(default="UTC", min_length=1, max_length=80)
    source_message_id: int | None = None
    requested_by_contact_id: int | None = None
    idempotency_key: str | None = Field(default=None, max_length=160)


class RescheduleIn(BaseModel):
    scheduled_for: datetime
    timezone: str | None = Field(default=None, max_length=80)


def _http_error(exc: ValueError) -> HTTPException:
    resolution = getattr(exc, "resolution", None)
    if resolution:
        return HTTPException(status_code=409, detail={"message": str(exc), "resolution": resolution})
    if "not found" in str(exc):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=409, detail=str(exc))


@router.post("")
async def create_scheduled_message(
    payload: ScheduledMessageIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = ScheduledActionService(db)
    try:
        item = await service.create_whatsapp_message(
            target_reference=payload.target,
            text=payload.text,
            scheduled_for=payload.scheduled_for,
            timezone=payload.timezone,
            source_message_id=payload.source_message_id,
            requested_by_contact_id=payload.requested_by_contact_id,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}


@router.get("")
async def list_scheduled_actions(
    status: str | None = Query(default=None, max_length=24),
    limit: int = Query(default=100, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    items = await ScheduledActionService(db).list(status=status, limit=limit)
    return {"count": len(items), "items": items}


@router.post("/{action_id}/cancel")
async def cancel_scheduled_action(action_id: int, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    try:
        item = await ScheduledActionService(db).cancel(action_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}


@router.post("/{action_id}/pause")
async def pause_scheduled_action(action_id: int, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    try:
        item = await ScheduledActionService(db).pause(action_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}


@router.post("/{action_id}/resume")
async def resume_scheduled_action(action_id: int, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    try:
        item = await ScheduledActionService(db).resume(action_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}


@router.post("/{action_id}/run-now")
async def run_scheduled_action_now(action_id: int, db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    try:
        item = await ScheduledActionService(db).run_now(action_id)
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}


@router.post("/{action_id}/reschedule")
async def reschedule_action(
    action_id: int,
    payload: RescheduleIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    try:
        item = await ScheduledActionService(db).reschedule(
            action_id,
            scheduled_for=payload.scheduled_for,
            timezone=payload.timezone,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    await db.commit()
    return {"ok": True, "item": item}

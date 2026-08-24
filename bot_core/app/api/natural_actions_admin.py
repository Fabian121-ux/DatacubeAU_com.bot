from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.services.natural_action_planner_service import DEFAULT_OWNER_TIMEZONE, NaturalActionPlannerService


router = APIRouter(
    prefix="/admin/natural-actions",
    tags=["admin"],
    dependencies=[Depends(require_admin_session)],
)


class NaturalActionIn(BaseModel):
    instruction: str = Field(min_length=1, max_length=8000)
    timezone: str = Field(default=DEFAULT_OWNER_TIMEZONE, min_length=1, max_length=80)
    source_message_id: int | None = None
    requested_by_contact_id: int | None = None
    idempotency_key: str | None = Field(default=None, max_length=160)


def _http_error(exc: ValueError) -> HTTPException:
    resolution = getattr(exc, "resolution", None)
    if resolution:
        return HTTPException(status_code=409, detail={"message": str(exc), "resolution": resolution})
    return HTTPException(status_code=409, detail=str(exc))


@router.post("/whatsapp-message")
async def create_natural_whatsapp_action(
    payload: NaturalActionIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = NaturalActionPlannerService(db)
    try:
        result = await service.create_from_instruction(
            payload.instruction,
            timezone=payload.timezone,
            source_message_id=payload.source_message_id,
            requested_by_contact_id=payload.requested_by_contact_id,
            idempotency_key=payload.idempotency_key,
        )
    except ValueError as exc:
        raise _http_error(exc) from exc
    if result is None:
        raise HTTPException(
            status_code=422,
            detail=(
                "unsupported natural action; use a form such as "
                "'message Amanda at 9am tomorrow and tell her the document is ready'"
            ),
        )
    await db.commit()
    return {"ok": True, **result}

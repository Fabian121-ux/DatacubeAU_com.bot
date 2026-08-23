from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.db import get_db_session
from app.services.conversation_takeover_service import ConversationTakeoverService


router = APIRouter(
    prefix="/admin/conversation-takeovers",
    tags=["admin"],
    dependencies=[Depends(require_admin_session)],
)


class ConversationTakeoverControlIn(BaseModel):
    auto_assist_enabled: bool
    inactivity_seconds: int | None = Field(default=None, ge=5, le=86400)
    wait_for_fabian_first: bool | None = None


@router.get("/{chat_id}")
async def get_conversation_takeover_control(
    chat_id: str,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await ConversationTakeoverService(db).get_chat_control(chat_id=chat_id)


@router.put("/{chat_id}")
async def set_conversation_takeover_control(
    chat_id: str,
    body: ConversationTakeoverControlIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    result = await ConversationTakeoverService(db).set_chat_control(
        chat_id=chat_id,
        auto_assist_enabled=body.auto_assist_enabled,
        inactivity_seconds=body.inactivity_seconds,
        wait_for_fabian_first=body.wait_for_fabian_first,
    )
    await db.commit()
    return result

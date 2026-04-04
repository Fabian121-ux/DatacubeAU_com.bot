from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.core.router import InboundRouter
from app.db import get_db_session
from app.models.enums import ChatType, GroupReplyMode
from app.models.schema import AuditLog, Contact, GroupConfig, Message, RouterDecision
from app.utils.text import normalize_text
from app.utils.time import utcnow


router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin_token(x_admin_token: str | None) -> None:
    if settings.admin_api_token and x_admin_token != settings.admin_api_token:
        raise HTTPException(status_code=401, detail="invalid admin token")


class TestReplyIn(BaseModel):
    message_text: str
    chat_type: ChatType = ChatType.DM
    chat_id: str = "local-preview"
    sender_id: str = "preview-user@c.us"
    sender_name: str | None = "Preview User"
    is_bot_mentioned: bool = False


class GroupModeIn(BaseModel):
    chat_id: str
    reply_mode: GroupReplyMode = GroupReplyMode.MENTION_ONLY
    is_enabled: bool = True
    cooldown_seconds: int = Field(default=45, ge=0, le=3600)


@router.get("/logs/recent")
async def recent_logs(
    x_admin_token: str | None = Header(default=None),
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "action": row.action,
                "entity_type": row.entity_type,
                "entity_id": row.entity_id,
                "details_json": row.details_json,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.get("/router-decisions/recent")
async def recent_router_decisions(
    x_admin_token: str | None = Header(default=None),
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    stmt = select(RouterDecision).order_by(RouterDecision.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "message_id": row.message_id,
                "decision_type": row.decision_type,
                "reason": row.reason,
                "confidence": row.confidence,
                "reply_sent": row.reply_sent,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.get("/messages/recent")
async def recent_messages(
    x_admin_token: str | None = Header(default=None),
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    stmt = select(Message).order_by(Message.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "chat_id": row.chat_id,
                "chat_type": row.chat_type,
                "direction": row.direction,
                "message_text": row.message_text,
                "message_type": row.message_type,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


@router.post("/test-reply")
async def test_reply(
    payload: TestReplyIn,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    router_service = InboundRouter(db)
    try:
        contact = None
        stmt = select(Contact).where(Contact.whatsapp_id == payload.sender_id).limit(1)
        contact = (await db.execute(stmt)).scalar_one_or_none()
        normalized = NormalizedMessage(
            chat_id=payload.chat_id,
            sender_id=payload.sender_id,
            sender_name=payload.sender_name,
            chat_type=payload.chat_type,
            message_text=payload.message_text,
            normalized_text=normalize_text(payload.message_text),
            message_type="text",
            is_bot_mentioned=payload.is_bot_mentioned,
            payload={"source": "admin_test_reply"},
        )
        planned = await router_service.preview(normalized, contact.id if contact else None)
        return {
            "decision_type": planned.decision_type.value,
            "reason": planned.reason,
            "should_reply": planned.should_reply,
            "reply_text": planned.reply_text,
            "kb_confidence": planned.kb_confidence,
            "matched_chunks": planned.matched_chunks,
            "ai_used": planned.ai_used,
        }
    finally:
        await router_service.close()


@router.post("/group-mode")
async def update_group_mode(
    payload: GroupModeIn,
    x_admin_token: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    require_admin_token(x_admin_token)
    stmt = select(GroupConfig).where(GroupConfig.chat_id == payload.chat_id).limit(1)
    model = (await db.execute(stmt)).scalar_one_or_none()
    if model:
        model.reply_mode = payload.reply_mode.value
        model.is_enabled = payload.is_enabled
        model.cooldown_seconds = payload.cooldown_seconds
        model.updated_at = utcnow()
    else:
        db.add(
            GroupConfig(
                chat_id=payload.chat_id,
                reply_mode=payload.reply_mode.value,
                is_enabled=payload.is_enabled,
                cooldown_seconds=payload.cooldown_seconds,
                updated_at=utcnow(),
            )
        )
    db.add(
        AuditLog(
            action="group_mode_updated",
            entity_type="group_config",
            entity_id=payload.chat_id,
            details_json=payload.model_dump(),
        )
    )
    await db.commit()
    return {"ok": True, "chat_id": payload.chat_id, "reply_mode": payload.reply_mode.value}


@router.get("/config/debug")
async def config_debug(x_admin_token: str | None = Header(default=None)) -> dict[str, object]:
    require_admin_token(x_admin_token)
    return settings.debug_view()

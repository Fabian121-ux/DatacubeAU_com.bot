from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_token
from app.config import settings
from app.core.message_normalizer import NormalizedMessage
from app.core.router import InboundRouter
from app.db import get_db_session
from app.models.enums import ChatType, GroupReplyMode
from app.models.schema import (
    AICall,
    AuditLog,
    BotConfig,
    Contact,
    GroupConfig,
    Message,
    QACache,
    ReplyRule,
    RouterDecision,
    UserMemory,
)
from app.services.bot_config_service import BotConfigService
from app.utils.text import normalize_text
from app.utils.time import utcnow


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_token)])


# ---------------------------------------------------------------------------
# Pydantic request models
# ---------------------------------------------------------------------------

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


class ReplyRuleIn(BaseModel):
    keyword: str
    response_text: str
    match_mode: str = "contains"
    chat_type_filter: str | None = None
    is_enabled: bool = True
    priority: int = 0


class ReplyRuleUpdate(BaseModel):
    keyword: str | None = None
    response_text: str | None = None
    match_mode: str | None = None
    chat_type_filter: str | None = None
    is_enabled: bool | None = None
    priority: int | None = None


class ConfigUpdate(BaseModel):
    key: str
    value: str


class MemoryUpdate(BaseModel):
    user_name: str | None = None
    preferences: str | None = None
    context_notes: str | None = None


# ---------------------------------------------------------------------------
# Existing endpoints (unchanged behavior)
# ---------------------------------------------------------------------------

@router.get("/logs/recent")
async def recent_logs(
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
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
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(RouterDecision, AICall.prompt_tokens, AICall.completion_tokens)
        .outerjoin(AICall, AICall.message_id == RouterDecision.message_id)
        .order_by(RouterDecision.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row[0].id,
                "message_id": row[0].message_id,
                "decision_type": row[0].decision_type,
                "reason": row[0].reason,
                "confidence": row[0].confidence,
                "reply_sent": row[0].reply_sent,
                "created_at": row[0].created_at,
                "ai_tokens": (row[1] or 0) + (row[2] or 0) if row[1] is not None or row[2] is not None else 0,
            }
            for row in rows
        ],
    }


@router.get("/messages/recent")
async def recent_messages(
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
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
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
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
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
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
async def config_debug() -> dict[str, object]:
    return settings.debug_view()


# ---------------------------------------------------------------------------
# Reply Rules CRUD
# ---------------------------------------------------------------------------

@router.get("/reply-rules")
async def list_reply_rules(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(ReplyRule).order_by(ReplyRule.priority.desc(), ReplyRule.id)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "keyword": r.keyword,
                "response_text": r.response_text,
                "match_mode": r.match_mode,
                "chat_type_filter": r.chat_type_filter,
                "is_enabled": r.is_enabled,
                "priority": r.priority,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.post("/reply-rules")
async def create_reply_rule(
    payload: ReplyRuleIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rule = ReplyRule(
        keyword=payload.keyword,
        response_text=payload.response_text,
        match_mode=payload.match_mode,
        chat_type_filter=payload.chat_type_filter,
        is_enabled=payload.is_enabled,
        priority=payload.priority,
        updated_at=utcnow(),
    )
    db.add(rule)
    db.add(AuditLog(action="reply_rule_created", entity_type="reply_rule", entity_id=None, details_json=payload.model_dump()))
    await db.commit()
    await db.refresh(rule)
    return {"ok": True, "id": rule.id}


@router.put("/reply-rules/{rule_id}")
async def update_reply_rule(
    rule_id: int,
    payload: ReplyRuleUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rule = await db.get(ReplyRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    if payload.keyword is not None:
        rule.keyword = payload.keyword
    if payload.response_text is not None:
        rule.response_text = payload.response_text
    if payload.match_mode is not None:
        rule.match_mode = payload.match_mode
    if payload.chat_type_filter is not None:
        rule.chat_type_filter = payload.chat_type_filter if payload.chat_type_filter != "" else None
    if payload.is_enabled is not None:
        rule.is_enabled = payload.is_enabled
    if payload.priority is not None:
        rule.priority = payload.priority
    rule.updated_at = utcnow()
    db.add(AuditLog(action="reply_rule_updated", entity_type="reply_rule", entity_id=str(rule_id), details_json=payload.model_dump(exclude_none=True)))
    await db.commit()
    return {"ok": True, "id": rule_id}


@router.delete("/reply-rules/{rule_id}")
async def delete_reply_rule(
    rule_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rule = await db.get(ReplyRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    await db.delete(rule)
    db.add(AuditLog(action="reply_rule_deleted", entity_type="reply_rule", entity_id=str(rule_id), details_json={}))
    await db.commit()
    return {"ok": True, "id": rule_id}


# ---------------------------------------------------------------------------
# Group Configs
# ---------------------------------------------------------------------------

@router.get("/groups")
async def list_groups(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(GroupConfig).order_by(GroupConfig.updated_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "chat_id": r.chat_id,
                "reply_mode": r.reply_mode,
                "is_enabled": r.is_enabled,
                "cooldown_seconds": r.cooldown_seconds,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


# ---------------------------------------------------------------------------
# Memory Management
# ---------------------------------------------------------------------------

@router.get("/memory")
async def list_memory(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(UserMemory, Contact)
        .join(Contact, Contact.id == UserMemory.contact_id)
        .order_by(UserMemory.updated_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": mem.id,
                "contact_id": mem.contact_id,
                "whatsapp_id": contact.whatsapp_id,
                "display_name": contact.display_name,
                "user_name": mem.user_name,
                "preferences": mem.preferences,
                "context_notes": mem.context_notes,
                "onboarding_complete": mem.onboarding_complete,
                "created_at": mem.created_at,
                "updated_at": mem.updated_at,
            }
            for mem, contact in rows
        ],
    }


@router.get("/memory/{contact_id}")
async def get_memory(
    contact_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(UserMemory).where(UserMemory.contact_id == contact_id).limit(1)
    mem = (await db.execute(stmt)).scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="memory not found for this contact")
    return {
        "id": mem.id,
        "contact_id": mem.contact_id,
        "user_name": mem.user_name,
        "preferences": mem.preferences,
        "context_notes": mem.context_notes,
        "onboarding_complete": mem.onboarding_complete,
        "created_at": mem.created_at,
        "updated_at": mem.updated_at,
    }


@router.put("/memory/{contact_id}")
async def update_memory(
    contact_id: int,
    payload: MemoryUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(UserMemory).where(UserMemory.contact_id == contact_id).limit(1)
    mem = (await db.execute(stmt)).scalar_one_or_none()
    if not mem:
        raise HTTPException(status_code=404, detail="memory not found for this contact")
    if payload.user_name is not None:
        mem.user_name = payload.user_name
    if payload.preferences is not None:
        mem.preferences = payload.preferences
    if payload.context_notes is not None:
        mem.context_notes = payload.context_notes
    mem.updated_at = utcnow()
    db.add(AuditLog(action="memory_updated", entity_type="user_memory", entity_id=str(contact_id), details_json=payload.model_dump(exclude_none=True)))
    await db.commit()
    return {"ok": True, "contact_id": contact_id}


@router.delete("/memory/{contact_id}")
async def delete_memory(
    contact_id: int,
    level: str = Query("high", description="low, medium, high, or critical"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(UserMemory).where(UserMemory.contact_id == contact_id).limit(1)
    mem = (await db.execute(stmt)).scalar_one_or_none()
    
    if not mem and level != "critical":
        raise HTTPException(status_code=404, detail="memory not found for this contact")
        
    action_details = {"level": level}
    
    if level == "low":
        if mem:
            mem.context_notes = None
            action_details["cleared"] = "context_notes"
            
    elif level == "medium":
        if mem:
            mem.preferences = None
            mem.context_notes = None
            action_details["cleared"] = "preferences, context_notes"
            
    elif level == "high":
        if mem:
            await db.delete(mem)
            action_details["cleared"] = "full_user_memory"
            
    elif level == "critical":
        if mem:
            await db.delete(mem)
        # Also clear conversation summaries for this contact
        contact_stmt = select(Contact.whatsapp_id).where(Contact.id == contact_id).limit(1)
        whatsapp_id = (await db.execute(contact_stmt)).scalar_one_or_none()
        if whatsapp_id:
            summary_stmt = delete(ConversationSession).where(ConversationSession.chat_id == whatsapp_id)
            await db.execute(summary_stmt)
            action_details["cleared"] = "full_user_memory, conversation_sessions"

    db.add(AuditLog(action="memory_cleared", entity_type="user_memory", entity_id=str(contact_id), details_json=action_details))
    await db.commit()
    return {"ok": True, "contact_id": contact_id, "level": level, "details": action_details}

@router.delete("/memory/all/critical")
async def clear_all_memory_critical(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    mem_res = await db.execute(delete(UserMemory))
    sess_res = await db.execute(delete(ConversationSession))
    db.add(AuditLog(action="all_memory_cleared_critical", entity_type="system", entity_id=None, details_json={"mem_deleted": mem_res.rowcount, "sess_deleted": sess_res.rowcount}))
    await db.commit()
    return {"ok": True, "mem_deleted": mem_res.rowcount, "sess_deleted": sess_res.rowcount}


# ---------------------------------------------------------------------------
# Bot Config
# ---------------------------------------------------------------------------

@router.get("/config")
async def get_config(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = BotConfigService(db)
    return {"config": await svc.get_all()}


@router.post("/config")
async def update_config(
    payload: ConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = BotConfigService(db)
    await svc.set(payload.key, payload.value)
    db.add(AuditLog(action="config_updated", entity_type="bot_config", entity_id=payload.key, details_json={"value": payload.value}))
    await db.commit()
    return {"ok": True, "key": payload.key, "value": payload.value}


# ---------------------------------------------------------------------------
# Cache Management
# ---------------------------------------------------------------------------

@router.get("/cache")
async def list_cache(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(QACache).order_by(QACache.hit_count.desc(), QACache.updated_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "normalized_question": r.normalized_question,
                "answer_text": r.answer_text,
                "answer_mode": r.answer_mode,
                "confidence": r.confidence,
                "hit_count": r.hit_count,
                "created_at": r.created_at,
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.delete("/cache/{cache_id}")
async def delete_cache_entry(
    cache_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    entry = await db.get(QACache, cache_id)
    if not entry:
        raise HTTPException(status_code=404, detail="cache entry not found")
    await db.delete(entry)
    await db.commit()
    return {"ok": True, "id": cache_id}


@router.post("/cache/clear")
async def clear_cache(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    result = await db.execute(delete(QACache))
    db.add(AuditLog(action="cache_cleared", entity_type="qa_cache", entity_id=None, details_json={"rows_deleted": result.rowcount}))
    await db.commit()
    return {"ok": True, "rows_deleted": result.rowcount}


# ---------------------------------------------------------------------------
# Usage / Stats
# ---------------------------------------------------------------------------

@router.get("/usage")
async def usage_stats(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

    # AI calls today
    ai_today_stmt = select(func.count(AICall.id)).where(AICall.created_at >= today_start)
    ai_calls_today = (await db.execute(ai_today_stmt)).scalar_one()

    # Tokens today
    tokens_stmt = select(
        func.coalesce(func.sum(AICall.prompt_tokens), 0),
        func.coalesce(func.sum(AICall.completion_tokens), 0),
    ).where(AICall.created_at >= today_start)
    prompt_tokens, completion_tokens = (await db.execute(tokens_stmt)).one()

    # Messages today
    msg_today_stmt = select(func.count(Message.id)).where(Message.created_at >= today_start)
    messages_today = (await db.execute(msg_today_stmt)).scalar_one()

    # Total AI calls (all time)
    ai_total_stmt = select(func.count(AICall.id))
    ai_calls_total = (await db.execute(ai_total_stmt)).scalar_one()

    # Total contacts
    contacts_stmt = select(func.count(Contact.id))
    total_contacts = (await db.execute(contacts_stmt)).scalar_one()

    # Cache size
    cache_stmt = select(func.count(QACache.id))
    cache_size = (await db.execute(cache_stmt)).scalar_one()

    # Memory count
    memory_stmt = select(func.count(UserMemory.id))
    memory_count = (await db.execute(memory_stmt)).scalar_one()

    return {
        "today": {
            "ai_calls": ai_calls_today,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "messages": messages_today,
        },
        "totals": {
            "ai_calls": ai_calls_total,
            "contacts": total_contacts,
            "cache_entries": cache_size,
            "memory_entries": memory_count,
        },
    }


# ---------------------------------------------------------------------------
# WAHA Session Controls
# ---------------------------------------------------------------------------

@router.post("/waha/start")
async def start_waha_session() -> dict[str, Any]:
    import httpx
    url = f"{settings.waha_service_url}/api/sessions/start"
    payload = {"name": settings.waha_session_name}
    headers = {"X-Api-Key": settings.waha_api_key} if settings.waha_api_key else {}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()
            return {"ok": True, "status": "starting"}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/waha/stop")
async def stop_waha_session() -> dict[str, Any]:
    import httpx
    url = f"{settings.waha_service_url}/api/sessions/stop"
    payload = {"name": settings.waha_session_name, "logout": False}
    headers = {"X-Api-Key": settings.waha_api_key} if settings.waha_api_key else {}
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(url, json=payload, headers=headers, timeout=30)
            res.raise_for_status()
            return {"ok": True, "status": "stopped"}
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=500, detail=str(exc)) from exc


# ---------------------------------------------------------------------------
# Storage & Cleanup
# ---------------------------------------------------------------------------

@router.get("/storage/size")
async def get_storage_size(db: AsyncSession = Depends(get_db_session)) -> dict[str, Any]:
    from sqlalchemy import text
    try:
        stmt = text("SELECT pg_database_size(current_database());")
        db_size_bytes = (await db.execute(stmt)).scalar_one()
        return {
            "database_size_bytes": db_size_bytes,
            "database_size_mb": round(db_size_bytes / (1024 * 1024), 2),
        }
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


@router.post("/storage/cleanup")
async def cleanup_storage(
    days_to_keep: int = Query(default=30, ge=1),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    from datetime import timedelta
    cutoff = utcnow() - timedelta(days=days_to_keep)

    # Delete old Router Decisions
    rd_stmt = delete(RouterDecision).where(RouterDecision.created_at < cutoff)
    rd_deleted = (await db.execute(rd_stmt)).rowcount

    # Delete old Messages
    msg_stmt = delete(Message).where(Message.created_at < cutoff)
    msg_deleted = (await db.execute(msg_stmt)).rowcount

    # Delete old Audit Logs
    al_stmt = delete(AuditLog).where(AuditLog.created_at < cutoff)
    al_deleted = (await db.execute(al_stmt)).rowcount

    # Delete old AI Calls
    ai_stmt = delete(AICall).where(AICall.created_at < cutoff)
    ai_deleted = (await db.execute(ai_stmt)).rowcount

    db.add(
        AuditLog(
            action="storage_cleanup",
            entity_type="system",
            entity_id=None,
            details_json={
                "days_kept": days_to_keep,
                "deleted_decisions": rd_deleted,
                "deleted_messages": msg_deleted,
                "deleted_audit_logs": al_deleted,
                "deleted_ai_calls": ai_deleted,
            },
        )
    )
    await db.commit()
    return {
        "ok": True,
        "days_kept": days_to_keep,
        "deleted": {
            "decisions": rd_deleted,
            "messages": msg_deleted,
            "audit_logs": al_deleted,
            "ai_calls": ai_deleted,
        },
    }

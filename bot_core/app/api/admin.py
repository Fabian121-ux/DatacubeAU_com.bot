from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
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
    ConversationSession,
    FAQEntry,
    GroupConfig,
    KnowledgeDocument,
    Message,
    OutboundMessage,
    QACache,
    ReplyRule,
    RouterDecision,
    UserMemory,
    UserMemoryTimeline,
)
from app.services.bot_config_service import BotConfigService
from app.services.faq_service import FAQService
from app.services.memory_service import MemoryService
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.text import normalize_text
from app.utils.time import utcnow


router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin_session)])
CORE_FAQ_PATH = Path(__file__).resolve().parents[2] / "core_faq.md"


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


class IdentityUpdate(BaseModel):
    assistant_name: str | None = None
    assistant_role: str | None = None
    owner_name: str | None = None
    owner_bio: str | None = None
    projects: str | None = None
    services: str | None = None
    skills: str | None = None
    interests: str | None = None
    current_focus: str | None = None
    communication_style: str | None = None


class FAQSaveIn(BaseModel):
    content: str


class MemoryUpdate(BaseModel):
    user_name: str | None = None
    preferences: str | None = None
    context_notes: str | None = None
    profession: str | None = None
    interests: str | None = None
    projects: str | None = None
    goals: str | None = None
    communication_style: str | None = None
    relationship: str | None = None


class ProfileUpdate(BaseModel):
    user_name: str | None = None
    preferences: str | None = None
    context_notes: str | None = None
    profession: str | None = None
    interests: str | None = None
    projects: str | None = None
    goals: str | None = None
    communication_style: str | None = None
    relationship: str | None = None
    onboarding_complete: bool | None = None


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
        select(
            RouterDecision,
            AICall.prompt_tokens,
            AICall.completion_tokens,
            AICall.model,
            AICall.prompt_hash,
            AICall.latency_ms,
        )
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
                "ai_model": row[3],
                "prompt_hash": row[4],
                "latency_ms": row[5] or 0,
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
        memory_count = (await db.execute(select(func.count(UserMemory.id)))).scalar_one()
        cache_count = (await db.execute(select(func.count(QACache.id)))).scalar_one()
        faq_count = (await db.execute(select(func.count(FAQEntry.id)).where(FAQEntry.is_enabled.is_(True)))).scalar_one()
        knowledge_count = (
            await db.execute(
                select(func.count(KnowledgeDocument.id))
                .where(KnowledgeDocument.is_enabled.is_(True))
                .where(KnowledgeDocument.status == "active")
            )
        ).scalar_one()
        return {
            "decision_type": planned.decision_type.value,
            "source": planned.source_diagnostics.get("source"),
            "reason": planned.reason,
            "should_reply": planned.should_reply,
            "reply_text": planned.reply_text,
            "kb_confidence": planned.kb_confidence,
            "matched_chunks": planned.matched_chunks,
            "source_diagnostics": planned.source_diagnostics,
            "debugger": {
                "memory_profiles": memory_count,
                "cache_entries": cache_count,
                "core_faq_entries": faq_count,
                "active_knowledge_documents": knowledge_count,
                "token_usage": planned.source_diagnostics.get("ai", {}) if planned.source_diagnostics else {},
            },
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
                "profession": mem.profession,
                "interests": mem.interests,
                "projects": mem.projects,
                "goals": mem.goals,
                "communication_style": mem.communication_style,
                "relationship": mem.relationship,
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
        "profession": mem.profession,
        "interests": mem.interests,
        "projects": mem.projects,
        "goals": mem.goals,
        "communication_style": mem.communication_style,
        "relationship": mem.relationship,
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
    profile_fields = ("profession", "interests", "projects", "goals", "communication_style", "relationship")
    timeline_updates: list[str] = []
    for field in profile_fields:
        value = getattr(payload, field)
        if value is not None:
            setattr(mem, field, value)
            timeline_updates.append(f"{field}: {value}")
    mem.updated_at = utcnow()
    for fact in timeline_updates:
        db.add(
            UserMemoryTimeline(
                contact_id=contact_id,
                memory_text=fact,
                source="admin",
                confidence=1.0,
                updated_at=utcnow(),
            )
        )
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
            await db.execute(delete(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == contact_id))
            action_details["cleared"] = "full_user_memory, memory_timeline"
            
    elif level == "critical":
        if mem:
            await db.delete(mem)
        await db.execute(delete(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == contact_id))
        # Also clear conversation summaries for this contact
        contact_stmt = select(Contact.whatsapp_id).where(Contact.id == contact_id).limit(1)
        whatsapp_id = (await db.execute(contact_stmt)).scalar_one_or_none()
        if whatsapp_id:
            summary_stmt = delete(ConversationSession).where(ConversationSession.chat_id == whatsapp_id)
            await db.execute(summary_stmt)
            action_details["cleared"] = "full_user_memory, memory_timeline, conversation_sessions"

    db.add(AuditLog(action="memory_cleared", entity_type="user_memory", entity_id=str(contact_id), details_json=action_details))
    await db.commit()
    return {"ok": True, "contact_id": contact_id, "level": level, "details": action_details}

@router.delete("/memory/all/critical")
async def clear_all_memory_critical(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    mem_res = await db.execute(delete(UserMemory))
    timeline_res = await db.execute(delete(UserMemoryTimeline))
    sess_res = await db.execute(delete(ConversationSession))
    db.add(AuditLog(action="all_memory_cleared_critical", entity_type="system", entity_id=None, details_json={"mem_deleted": mem_res.rowcount, "timeline_deleted": timeline_res.rowcount, "sess_deleted": sess_res.rowcount}))
    await db.commit()
    return {"ok": True, "mem_deleted": mem_res.rowcount, "timeline_deleted": timeline_res.rowcount, "sess_deleted": sess_res.rowcount}


@router.get("/memory/{contact_id}/timeline")
async def get_memory_timeline(
    contact_id: int,
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(UserMemoryTimeline)
        .where(UserMemoryTimeline.contact_id == contact_id)
        .order_by(UserMemoryTimeline.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "contact_id": contact_id,
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "memory_text": row.memory_text,
                "source": row.source,
                "confidence": row.confidence,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


@router.get("/profiles")
async def list_profiles(
    q: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(UserMemory, Contact)
        .join(Contact, Contact.id == UserMemory.contact_id)
        .order_by(UserMemory.updated_at.desc())
        .limit(limit)
    )
    if q:
        like = f"%{normalize_text(q)}%"
        display_like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.whatsapp_id.ilike(display_like),
                Contact.display_name.ilike(display_like),
                UserMemory.user_name.ilike(display_like),
                UserMemory.profession.ilike(display_like),
                UserMemory.interests.ilike(like),
                UserMemory.projects.ilike(like),
                UserMemory.goals.ilike(like),
            )
        )
    rows = (await db.execute(stmt)).all()
    return {
        "count": len(rows),
        "items": [_profile_payload(mem, contact) for mem, contact in rows],
    }


@router.put("/profiles/{contact_id}")
async def update_profile(
    contact_id: int,
    payload: ProfileUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    contact = await db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="contact not found")

    svc = MemoryService(db)
    mem = await svc.get_memory(contact_id)
    if not mem:
        mem = await svc.upsert_memory(contact_id)

    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        setattr(mem, field, value)
        if field in {"profession", "interests", "projects", "goals", "communication_style", "relationship"}:
            await svc.log_memory_fact(
                contact_id,
                memory_text=f"{field}: {value}",
                source="admin",
                confidence=1.0,
            )
    mem.updated_at = utcnow()
    db.add(AuditLog(action="profile_updated", entity_type="user_memory", entity_id=str(contact_id), details_json=updates))
    await db.commit()
    return {"ok": True, "contact_id": contact_id}


@router.delete("/profiles/{contact_id}")
async def delete_profile(
    contact_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    mem_result = await db.execute(delete(UserMemory).where(UserMemory.contact_id == contact_id))
    timeline_result = await db.execute(delete(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == contact_id))
    db.add(
        AuditLog(
            action="profile_deleted",
            entity_type="user_memory",
            entity_id=str(contact_id),
            details_json={"memory_deleted": mem_result.rowcount, "timeline_deleted": timeline_result.rowcount},
        )
    )
    await db.commit()
    return {
        "ok": True,
        "contact_id": contact_id,
        "memory_deleted": mem_result.rowcount,
        "timeline_deleted": timeline_result.rowcount,
    }


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


@router.get("/identity")
async def get_identity(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = BotConfigService(db)
    return {
        "identity": await svc.get_identity_profile(),
        "personality": await svc.get_personality_settings(),
    }


@router.put("/identity")
async def update_identity(
    payload: IdentityUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    key_map = {
        "assistant_name": "assistant_name",
        "assistant_role": "assistant_role",
        "owner_name": "owner_name",
        "owner_bio": "owner_bio",
        "projects": "identity_projects",
        "services": "identity_services",
        "skills": "identity_skills",
        "interests": "identity_interests",
        "current_focus": "identity_focus",
        "communication_style": "identity_style",
    }
    svc = BotConfigService(db)
    updates = payload.model_dump(exclude_none=True)
    for field, value in updates.items():
        await svc.set(key_map[field], value)
        if field == "owner_bio":
            await svc.set("identity_bio", value)
    db.add(AuditLog(action="identity_updated", entity_type="bot_config", entity_id="identity", details_json=updates))
    await db.commit()
    return {"ok": True, "updated": sorted(updates)}


@router.get("/identity/status")
async def identity_status(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = BotConfigService(db)
    identity = await svc.get_identity_profile()
    personality = await svc.get_personality_settings()

    faq_count = (await db.execute(select(func.count(FAQEntry.id)).where(FAQEntry.is_enabled.is_(True)))).scalar_one()
    memory_count = (await db.execute(select(func.count(UserMemory.id)))).scalar_one()
    cache_count = (await db.execute(select(func.count(QACache.id)))).scalar_one()
    source_rows = (
        await db.execute(
            select(KnowledgeDocument.source_type, func.count(KnowledgeDocument.id))
            .where(KnowledgeDocument.is_enabled.is_(True))
            .where(KnowledgeDocument.status == "active")
            .group_by(KnowledgeDocument.source_type)
        )
    ).all()
    return {
        "assistant_name": identity["assistant_name"],
        "assistant_role": identity["assistant_role"],
        "owner_name": identity["owner_name"],
        "active_personality_settings": personality,
        "active_knowledge_sources": {
            "core_faq_entries": faq_count,
            "knowledge_documents": {source: count for source, count in source_rows},
            "memory_profiles": memory_count,
            "qa_cache_entries": cache_count,
        },
    }


@router.get("/faq")
async def get_faq(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = CORE_FAQ_PATH.read_text(encoding="utf-8") if CORE_FAQ_PATH.exists() else ""
    rows = (await db.execute(select(FAQEntry).order_by(FAQEntry.id))).scalars().all()
    return {
        "path": str(CORE_FAQ_PATH),
        "content": content,
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "question": row.question,
                "answer": row.answer,
                "is_enabled": row.is_enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


@router.post("/faq/upload")
async def upload_faq(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not file.filename or not file.filename.lower().endswith((".md", ".txt")):
        raise HTTPException(status_code=400, detail="only .md and .txt FAQ files are supported")
    content = (await file.read()).decode("utf-8", errors="ignore")
    return await _save_and_sync_faq(content, db, action="faq_uploaded", filename=file.filename)


@router.post("/faq/save")
async def save_faq(
    payload: FAQSaveIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await _save_and_sync_faq(payload.content, db, action="faq_saved", filename=None)


@router.get("/queue")
async def list_queue(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(OutboundMessage).order_by(OutboundMessage.created_at.desc()).limit(limit)
    if status:
        stmt = stmt.where(OutboundMessage.status == status)
    rows = (await db.execute(stmt)).scalars().all()
    return {"count": len(rows), "items": [_queue_payload(row) for row in rows]}


@router.post("/queue/{queue_id}/resend")
async def resend_queue_message(
    queue_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    message = await db.get(OutboundMessage, queue_id)
    if not message:
        raise HTTPException(status_code=404, detail="queue message not found")
    message.status = "pending"
    message.retry_count = 0
    message.next_attempt_at = utcnow()
    message.error_message = None
    message.updated_at = utcnow()
    db.add(AuditLog(action="outbound_queue_resend", entity_type="outbound_queue", entity_id=str(queue_id), details_json={}))
    await db.commit()
    return {"ok": True, "id": queue_id}


@router.delete("/queue/{queue_id}")
async def delete_queue_message(
    queue_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    message = await db.get(OutboundMessage, queue_id)
    if not message:
        raise HTTPException(status_code=404, detail="queue message not found")
    await db.delete(message)
    db.add(AuditLog(action="outbound_queue_deleted", entity_type="outbound_queue", entity_id=str(queue_id), details_json={}))
    await db.commit()
    return {"ok": True, "id": queue_id}


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
    client = WAHAClient()
    try:
        payload = await client.start_session()
        return {"ok": True, "status": "starting", "response": payload}
    except WahaClientError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        await client.close()


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


@router.get("/waha/outages")
async def list_waha_outages(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    from app.models.schema import WahaOutage

    stmt = select(WahaOutage).order_by(WahaOutage.created_at.desc()).limit(limit)
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "previous_status": row.previous_status,
                "current_status": row.current_status,
                "reconnect_attempted": row.reconnect_attempted,
                "reconnect_success": row.reconnect_success,
                "details_json": row.details_json,
                "created_at": row.created_at,
            }
            for row in rows
        ],
    }


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


# ---------------------------------------------------------------------------
# Serialization / file helpers
# ---------------------------------------------------------------------------

async def _save_and_sync_faq(
    content: str,
    db: AsyncSession,
    *,
    action: str,
    filename: str | None,
) -> dict[str, Any]:
    if not content.strip():
        raise HTTPException(status_code=400, detail="FAQ content is empty")
    CORE_FAQ_PATH.write_text(content, encoding="utf-8")
    service = FAQService(db)
    pairs = service.parse_faq_text(content)
    count = await service.sync_faq_in_db(pairs)
    db.add(
        AuditLog(
            action=action,
            entity_type="faq_entries",
            entity_id=None,
            details_json={"filename": filename, "entries": count, "path": str(CORE_FAQ_PATH)},
        )
    )
    await db.commit()
    return {"ok": True, "entries": count, "path": str(CORE_FAQ_PATH)}


def _queue_payload(row: OutboundMessage) -> dict[str, Any]:
    return {
        "id": row.id,
        "chat_id": row.chat_id,
        "message_text": row.message_text,
        "status": row.status,
        "retry_count": row.retry_count,
        "max_retries": row.max_retries,
        "next_attempt_at": row.next_attempt_at,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _profile_payload(mem: UserMemory, contact: Contact) -> dict[str, Any]:
    return {
        "id": mem.id,
        "contact_id": mem.contact_id,
        "whatsapp_id": contact.whatsapp_id,
        "display_name": contact.display_name,
        "user_name": mem.user_name,
        "preferences": mem.preferences,
        "context_notes": mem.context_notes,
        "onboarding_complete": mem.onboarding_complete,
        "profession": mem.profession,
        "interests": mem.interests,
        "projects": mem.projects,
        "goals": mem.goals,
        "communication_style": mem.communication_style,
        "relationship": mem.relationship,
        "created_at": mem.created_at,
        "updated_at": mem.updated_at,
    }

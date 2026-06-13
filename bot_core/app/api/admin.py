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
    AIUsageEvent,
    AIUsageQuota,
    AuditLog,
    BotConfig,
    Contact,
    ConversationSession,
    ConversationSummary,
    ConversationTimeline,
    FAQEntry,
    GroupConfig,
    IdentityRegistryEntry,
    InternetCache,
    InternetUsageEvent,
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
from app.services.command_catalog_service import CommandCatalogService
from app.services.faq_service import FAQService
from app.services.identity_registry_service import IdentityRegistryService
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


class FAQImportIn(BaseModel):
    content: str
    source_name: str | None = None
    category: str = "General"


class CommandToggleIn(BaseModel):
    name: str
    enabled: bool


class IdentityRegistryUpdate(BaseModel):
    registry_key: str
    category: str | None = None
    name: str | None = None
    description: str | None = None
    aliases: list[str] | None = None
    keywords: list[str] | None = None
    entities: list[str] | None = None
    answer: str | None = None
    facts_json: dict[str, Any] | None = None
    enabled: bool | None = None


class MemoryUpdate(BaseModel):
    display_name: str | None = None
    user_name: str | None = None
    preferences: str | None = None
    context_notes: str | None = None
    profession: str | None = None
    interests: str | None = None
    projects: str | None = None
    goals: str | None = None
    communication_style: str | None = None
    relationship: str | None = None
    relationship_type: str | None = None
    personality_notes: str | None = None


class ProfileUpdate(BaseModel):
    display_name: str | None = None
    user_name: str | None = None
    preferences: str | None = None
    context_notes: str | None = None
    profession: str | None = None
    interests: str | None = None
    projects: str | None = None
    goals: str | None = None
    communication_style: str | None = None
    relationship: str | None = None
    relationship_type: str | None = None
    personality_notes: str | None = None
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
    decision_ids = [str(row[0].id) for row in rows]
    audit_map: dict[str, dict[str, Any]] = {}
    if decision_ids:
        audit_rows = (
            await db.execute(
                select(AuditLog.entity_id, AuditLog.details_json)
                .where(AuditLog.action == "router_decision")
                .where(AuditLog.entity_id.in_(decision_ids))
            )
        ).all()
        audit_map = {
            str(entity_id): details_json or {}
            for entity_id, details_json in audit_rows
            if entity_id is not None
        }
    inbound_ids = [row[0].message_id for row in rows]
    inbound_map: dict[int, Message] = {}
    final_response_map: dict[int, str] = {}
    if inbound_ids:
        inbound_messages = (
            await db.execute(select(Message).where(Message.id.in_(inbound_ids)))
        ).scalars().all()
        inbound_map = {message.id: message for message in inbound_messages}
        chat_ids = sorted({message.chat_id for message in inbound_messages})
        outbound_messages = (
            await db.execute(
                select(Message)
                .where(Message.direction == "outbound")
                .where(Message.chat_id.in_(chat_ids))
                .order_by(Message.created_at.asc())
            )
        ).scalars().all()
        for inbound in inbound_messages:
            final = next(
                (
                    outbound
                    for outbound in outbound_messages
                    if outbound.chat_id == inbound.chat_id and outbound.created_at >= inbound.created_at
                ),
                None,
            )
            if final:
                final_response_map[inbound.id] = final.message_text
    return {
        "count": len(rows),
        "items": [
            {
                "id": row[0].id,
                "message_id": row[0].message_id,
                "message": (inbound_map.get(row[0].message_id).message_text if inbound_map.get(row[0].message_id) else None),
                "question": audit_map.get(str(row[0].id), {}).get("question"),
                "intent": audit_map.get(str(row[0].id), {}).get("intent"),
                "decision_type": row[0].decision_type,
                "reason": row[0].reason,
                "confidence": row[0].confidence,
                "reply_sent": row[0].reply_sent,
                "created_at": row[0].created_at,
                "ai_tokens": (row[1] or 0) + (row[2] or 0) if row[1] is not None or row[2] is not None else 0,
                "ai_model": row[3],
                "prompt_hash": row[4],
                "latency_ms": row[5] or 0,
                "router_analytics": audit_map.get(str(row[0].id), {}).get("router_analytics") or {},
                "source_diagnostics": audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {},
                "expanded_query": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("expanded_query"),
                "topic": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("topic"),
                "entities": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("entities") or [],
                "memory_hits": ((audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("hits") or {}).get("memory", 0),
                "faq_hits": ((audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("hits") or {}).get("faq", 0),
                "knowledge_hits": ((audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("hits") or {}).get("knowledge", 0),
                "internet_hits": ((audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("hits") or {}).get("internet", 0),
                "ai_hits": ((audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("hits") or {}).get("ai", 0),
                "selected_source": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("selected_source"),
                "selected_route": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("selected_route"),
                "rejected_routes": (audit_map.get(str(row[0].id), {}).get("router_analytics") or {}).get("rejected_routes") or [],
                "final_response": final_response_map.get(row[0].message_id),
            }
            for row in rows
        ],
    }


@router.get("/conversation-inspector")
async def conversation_inspector(
    limit: int = Query(default=settings.recent_items_limit, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await recent_router_decisions(limit=limit, db=db)


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
                "memory": planned.source_diagnostics.get("memory", {}) if planned.source_diagnostics else {},
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
                "display_name": mem.display_name or contact.display_name,
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
                "relationship_type": mem.relationship_type,
                "personality_notes": mem.personality_notes,
                "first_seen_at": mem.first_seen_at,
                "last_interaction_at": mem.last_interaction_at,
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
        "display_name": mem.display_name,
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
        "relationship_type": mem.relationship_type,
        "personality_notes": mem.personality_notes,
        "first_seen_at": mem.first_seen_at,
        "last_interaction_at": mem.last_interaction_at,
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
    if payload.display_name is not None:
        mem.display_name = payload.display_name
        contact = await db.get(Contact, contact_id)
        if contact:
            contact.display_name = payload.display_name
    if payload.user_name is not None:
        mem.user_name = payload.user_name
    if payload.preferences is not None:
        mem.preferences = payload.preferences
    if payload.context_notes is not None:
        mem.context_notes = payload.context_notes
    profile_fields = (
        "profession",
        "interests",
        "projects",
        "goals",
        "communication_style",
        "relationship",
        "personality_notes",
    )
    timeline_updates: list[str] = []
    for field in profile_fields:
        value = getattr(payload, field)
        if value is not None:
            setattr(mem, field, value)
            timeline_updates.append(f"{field}: {value}")
    if payload.relationship_type is not None:
        mem.relationship_type = MemoryService.normalize_relationship_type(payload.relationship_type)
        timeline_updates.append(f"relationship_type: {mem.relationship_type}")
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
            await db.execute(delete(ConversationTimeline).where(ConversationTimeline.contact_id == contact_id))
            await db.execute(delete(ConversationSummary).where(ConversationSummary.contact_id == contact_id))
            action_details["cleared"] = "full_user_memory, memory_timeline, conversation_timeline, conversation_summaries"
            
    elif level == "critical":
        if mem:
            await db.delete(mem)
        await db.execute(delete(UserMemoryTimeline).where(UserMemoryTimeline.contact_id == contact_id))
        await db.execute(delete(ConversationTimeline).where(ConversationTimeline.contact_id == contact_id))
        await db.execute(delete(ConversationSummary).where(ConversationSummary.contact_id == contact_id))
        # Also clear conversation summaries for this contact
        contact_stmt = select(Contact.whatsapp_id).where(Contact.id == contact_id).limit(1)
        whatsapp_id = (await db.execute(contact_stmt)).scalar_one_or_none()
        if whatsapp_id:
            summary_stmt = delete(ConversationSession).where(ConversationSession.chat_id == whatsapp_id)
            await db.execute(summary_stmt)
            action_details["cleared"] = "full_user_memory, memory_timeline, conversation_timeline, conversation_summaries, conversation_sessions"

    db.add(AuditLog(action="memory_cleared", entity_type="user_memory", entity_id=str(contact_id), details_json=action_details))
    await db.commit()
    return {"ok": True, "contact_id": contact_id, "level": level, "details": action_details}

@router.delete("/memory/all/critical")
async def clear_all_memory_critical(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    mem_res = await db.execute(delete(UserMemory))
    timeline_res = await db.execute(delete(UserMemoryTimeline))
    conversation_timeline_res = await db.execute(delete(ConversationTimeline))
    conversation_summary_res = await db.execute(delete(ConversationSummary))
    sess_res = await db.execute(delete(ConversationSession))
    db.add(AuditLog(action="all_memory_cleared_critical", entity_type="system", entity_id=None, details_json={"mem_deleted": mem_res.rowcount, "timeline_deleted": timeline_res.rowcount, "conversation_timeline_deleted": conversation_timeline_res.rowcount, "conversation_summaries_deleted": conversation_summary_res.rowcount, "sess_deleted": sess_res.rowcount}))
    await db.commit()
    return {
        "ok": True,
        "mem_deleted": mem_res.rowcount,
        "timeline_deleted": timeline_res.rowcount,
        "conversation_timeline_deleted": conversation_timeline_res.rowcount,
        "conversation_summaries_deleted": conversation_summary_res.rowcount,
        "sess_deleted": sess_res.rowcount,
    }


@router.get("/memory/{contact_id}/timeline")
async def get_memory_timeline(
    contact_id: int,
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    conversation_stmt = (
        select(ConversationTimeline)
        .where(ConversationTimeline.contact_id == contact_id)
        .order_by(ConversationTimeline.timestamp.desc())
        .limit(limit)
    )
    conversation_rows = (await db.execute(conversation_stmt)).scalars().all()
    legacy_stmt = (
        select(UserMemoryTimeline)
        .where(UserMemoryTimeline.contact_id == contact_id)
        .order_by(UserMemoryTimeline.created_at.desc())
        .limit(limit)
    )
    legacy_rows = (await db.execute(legacy_stmt)).scalars().all()
    items = [
        {
            "id": row.id,
            "type": "conversation",
            "topic": row.topic,
            "summary": row.summary,
            "memory_text": row.summary,
            "source": row.source,
            "importance_score": row.importance_score,
            "confidence": row.importance_score,
            "timestamp": row.timestamp,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in conversation_rows
    ]
    items.extend(
        {
            "id": row.id,
            "type": "profile_fact",
            "topic": "Profile fact",
            "summary": row.memory_text,
            "memory_text": row.memory_text,
            "source": row.source,
            "importance_score": row.confidence,
            "confidence": row.confidence,
            "timestamp": row.created_at,
            "created_at": row.created_at,
            "updated_at": row.updated_at,
        }
        for row in legacy_rows
    )
    items.sort(key=lambda item: item["timestamp"], reverse=True)
    return {
        "contact_id": contact_id,
        "count": len(items[:limit]),
        "items": items[:limit],
    }


@router.delete("/memory/{contact_id}/timeline/{timeline_id}")
async def delete_conversation_timeline_entry(
    contact_id: int,
    timeline_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = MemoryService(db)
    deleted = await svc.delete_timeline_entry(contact_id, timeline_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="timeline entry not found for this contact")
    db.add(
        AuditLog(
            action="conversation_timeline_deleted",
            entity_type="conversation_timeline",
            entity_id=str(timeline_id),
            details_json={"contact_id": contact_id},
        )
    )
    await db.commit()
    return {"ok": True, "contact_id": contact_id, "id": timeline_id}


@router.get("/memory/{contact_id}/summaries")
async def get_memory_summaries(
    contact_id: int,
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(ConversationSummary)
        .where(ConversationSummary.contact_id == contact_id)
        .order_by(ConversationSummary.created_at.desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).scalars().all()
    return {
        "contact_id": contact_id,
        "count": len(rows),
        "items": [
            {
                "id": row.id,
                "summary": row.summary,
                "topics": row.topics or [],
                "message_count": row.message_count,
                "threshold": row.threshold,
                "source": row.source,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
            for row in rows
        ],
    }


@router.delete("/memory/{contact_id}/summaries/{summary_id}")
async def delete_memory_summary(
    contact_id: int,
    summary_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = MemoryService(db)
    deleted = await svc.delete_summary(contact_id, summary_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="summary not found for this contact")
    db.add(
        AuditLog(
            action="conversation_summary_deleted",
            entity_type="conversation_summary",
            entity_id=str(summary_id),
            details_json={"contact_id": contact_id},
        )
    )
    await db.commit()
    return {"ok": True, "contact_id": contact_id, "id": summary_id}


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
                UserMemory.display_name.ilike(display_like),
                UserMemory.user_name.ilike(display_like),
                UserMemory.profession.ilike(display_like),
                UserMemory.interests.ilike(like),
                UserMemory.projects.ilike(like),
                UserMemory.goals.ilike(like),
                UserMemory.relationship_type.ilike(like),
                UserMemory.personality_notes.ilike(like),
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
        if field == "display_name":
            contact.display_name = value
        if field == "relationship_type":
            value = MemoryService.normalize_relationship_type(value)
        setattr(mem, field, value)
        if field in {
            "profession",
            "interests",
            "projects",
            "goals",
            "communication_style",
            "relationship",
            "relationship_type",
            "personality_notes",
        }:
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
    conversation_timeline_result = await db.execute(delete(ConversationTimeline).where(ConversationTimeline.contact_id == contact_id))
    summary_result = await db.execute(delete(ConversationSummary).where(ConversationSummary.contact_id == contact_id))
    db.add(
        AuditLog(
            action="profile_deleted",
            entity_type="user_memory",
            entity_id=str(contact_id),
            details_json={
                "memory_deleted": mem_result.rowcount,
                "timeline_deleted": timeline_result.rowcount,
                "conversation_timeline_deleted": conversation_timeline_result.rowcount,
                "summaries_deleted": summary_result.rowcount,
            },
        )
    )
    await db.commit()
    return {
        "ok": True,
        "contact_id": contact_id,
        "memory_deleted": mem_result.rowcount,
        "timeline_deleted": timeline_result.rowcount,
        "conversation_timeline_deleted": conversation_timeline_result.rowcount,
        "summaries_deleted": summary_result.rowcount,
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
    timeline_count = (await db.execute(select(func.count(ConversationTimeline.id)))).scalar_one()
    summary_count = (await db.execute(select(func.count(ConversationSummary.id)))).scalar_one()
    cache_count = (await db.execute(select(func.count(QACache.id)))).scalar_one()
    identity_count = (await db.execute(select(func.count(IdentityRegistryEntry.id)).where(IdentityRegistryEntry.is_enabled.is_(True)))).scalar_one()
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
            "conversation_timeline_entries": timeline_count,
            "conversation_summaries": summary_count,
            "qa_cache_entries": cache_count,
            "identity_registry_entries": identity_count,
        },
    }


@router.get("/identity/registry")
async def get_identity_registry(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    svc = IdentityRegistryService(db)
    entries = await svc.enabled_entries()
    return {"count": len(entries), "items": [svc.serialize(row) for row in entries]}


@router.post("/identity/registry")
async def upsert_identity_registry(
    payload: IdentityRegistryUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    key = payload.registry_key.strip()
    if not key:
        raise HTTPException(status_code=400, detail="registry_key is required")
    row = (
        await db.execute(select(IdentityRegistryEntry).where(IdentityRegistryEntry.registry_key == key).limit(1))
    ).scalar_one_or_none()
    if not row:
        if not payload.name or not payload.description or not payload.answer:
            raise HTTPException(status_code=400, detail="name, description, and answer are required for a new identity registry entry")
        row = IdentityRegistryEntry(
            registry_key=key,
            category=payload.category or "Identity",
            name=payload.name,
            description=payload.description,
            aliases=payload.aliases or [],
            keywords=payload.keywords or [],
            entities=payload.entities or [],
            answer=payload.answer,
            facts_json=payload.facts_json or {},
            is_enabled=True if payload.enabled is None else payload.enabled,
            created_at=utcnow(),
            updated_at=utcnow(),
        )
        db.add(row)
    else:
        for field in ("category", "name", "description", "aliases", "keywords", "entities", "answer", "facts_json"):
            value = getattr(payload, field)
            if value is not None:
                setattr(row, field, value)
        if payload.enabled is not None:
            row.is_enabled = payload.enabled
        row.updated_at = utcnow()
    db.add(AuditLog(action="identity_registry_updated", entity_type="identity_registry", entity_id=key, details_json={"registry_key": key}))
    await db.commit()
    return {"ok": True, "item": IdentityRegistryService.serialize(row)}


@router.get("/faq")
async def get_faq(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = CORE_FAQ_PATH.read_text(encoding="utf-8") if CORE_FAQ_PATH.exists() else ""
    rows = (await db.execute(select(FAQEntry).order_by(FAQEntry.id))).scalars().all()
    analytics = await FAQService(db).analytics()
    return {
        "path": str(CORE_FAQ_PATH),
        "content": content,
        "count": len(rows),
        "items": [FAQService.serialize_entry(row) for row in rows],
        "analytics": analytics,
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


@router.get("/faq/analytics")
async def faq_analytics(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await FAQService(db).analytics()


@router.post("/faq/import")
async def import_faq(
    payload: FAQImportIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="FAQ import content is empty")
    service = FAQService(db)
    result = await service.import_candidates(
        payload.content,
        source_name=payload.source_name or "admin",
        default_category=payload.category,
    )
    db.add(
        AuditLog(
            action="faq_imported",
            entity_type="faq_import_candidates",
            entity_id=None,
            details_json=result,
        )
    )
    await db.commit()
    return {"ok": True, **result}


@router.get("/faq/candidates")
async def faq_candidates(
    status: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = FAQService(db)
    rows = await service.list_candidates(status=status, limit=limit)
    return {"count": len(rows), "items": [service.serialize_candidate(row) for row in rows]}


@router.post("/faq/candidates/{candidate_id}/approve")
async def approve_faq_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = FAQService(db)
    try:
        entry = await service.approve_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="faq_candidate_approved",
            entity_type="faq_entries",
            entity_id=str(entry.id),
            details_json={"candidate_id": candidate_id, "refresh": _knowledge_refresh_targets()},
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize_entry(entry)}


@router.post("/faq/candidates/{candidate_id}/reject")
async def reject_faq_candidate(
    candidate_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = FAQService(db)
    try:
        candidate = await service.reject_candidate(candidate_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="faq_candidate_rejected",
            entity_type="faq_import_candidates",
            entity_id=str(candidate.id),
            details_json={"candidate_id": candidate_id},
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize_candidate(candidate)}


@router.get("/commands")
async def list_commands(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = CommandCatalogService(db)
    items = await service.list_commands()
    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        sections.setdefault(item["category"], []).append(item)
    return {"count": len(items), "sections": sections, "items": items}


@router.post("/commands/toggle")
async def toggle_command(
    payload: CommandToggleIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = CommandCatalogService(db)
    try:
        row = await service.set_enabled(payload.name, payload.enabled)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="command_catalog_updated",
            entity_type="command_catalog",
            entity_id=payload.name,
            details_json={"enabled": payload.enabled},
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize(row)}


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

    internet_today_stmt = select(func.count(InternetUsageEvent.id)).where(InternetUsageEvent.created_at >= today_start)
    internet_requests_today = (await db.execute(internet_today_stmt)).scalar_one()

    # Total AI calls (all time)
    ai_total_stmt = select(func.count(AICall.id))
    ai_calls_total = (await db.execute(ai_total_stmt)).scalar_one()

    # Total contacts
    contacts_stmt = select(func.count(Contact.id))
    total_contacts = (await db.execute(contacts_stmt)).scalar_one()

    # Cache size
    cache_stmt = select(func.count(QACache.id))
    cache_size = (await db.execute(cache_stmt)).scalar_one()
    internet_cache_size = (await db.execute(select(func.count(InternetCache.id)))).scalar_one()

    # Memory count
    memory_stmt = select(func.count(UserMemory.id))
    memory_count = (await db.execute(memory_stmt)).scalar_one()
    timeline_count = (await db.execute(select(func.count(ConversationTimeline.id)))).scalar_one()
    summary_count = (await db.execute(select(func.count(ConversationSummary.id)))).scalar_one()

    return {
        "today": {
            "ai_calls": ai_calls_today,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
            "messages": messages_today,
            "internet_requests": internet_requests_today,
        },
        "totals": {
            "ai_calls": ai_calls_total,
            "contacts": total_contacts,
            "cache_entries": cache_size,
            "internet_cache_entries": internet_cache_size,
            "memory_entries": memory_count,
            "conversation_timeline_entries": timeline_count,
            "conversation_summaries": summary_count,
        },
    }


@router.get("/ai-usage")
async def ai_usage_dashboard(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    today_stats = await _ai_usage_totals(db, today_start)
    month_stats = await _ai_usage_totals(db, month_start)

    top_rows = (
        await db.execute(
            select(
                Contact.id,
                Contact.whatsapp_id,
                Contact.display_name,
                func.count(AIUsageEvent.id).label("ai_calls"),
                func.coalesce(func.sum(AIUsageEvent.total_tokens), 0).label("total_tokens"),
            )
            .join(Contact, Contact.id == AIUsageEvent.contact_id)
            .where(AIUsageEvent.created_at >= month_start)
            .group_by(Contact.id, Contact.whatsapp_id, Contact.display_name)
            .order_by(func.coalesce(func.sum(AIUsageEvent.total_tokens), 0).desc())
            .limit(10)
        )
    ).all()

    recent_rows = (
        await db.execute(
            select(AIUsageEvent, Contact)
            .join(Contact, Contact.id == AIUsageEvent.contact_id)
            .order_by(AIUsageEvent.created_at.desc())
            .limit(limit)
        )
    ).all()

    quota_rows = (
        await db.execute(
            select(AIUsageQuota, Contact)
            .join(Contact, Contact.id == AIUsageQuota.contact_id)
            .order_by(AIUsageQuota.usage_count.desc(), AIUsageQuota.updated_at.desc())
            .limit(limit)
        )
    ).all()

    return {
        "today": today_stats,
        "month": month_stats,
        "top_users": [
            {
                "contact_id": contact_id,
                "whatsapp_id": whatsapp_id,
                "display_name": display_name,
                "ai_calls": int(ai_calls or 0),
                "total_tokens": int(total_tokens or 0),
            }
            for contact_id, whatsapp_id, display_name, ai_calls, total_tokens in top_rows
        ],
        "recent": [
            {
                "id": event.id,
                "contact_id": event.contact_id,
                "whatsapp_id": contact.whatsapp_id,
                "display_name": contact.display_name,
                "model": event.model,
                "mode": event.mode,
                "prompt_tokens": event.prompt_tokens,
                "completion_tokens": event.completion_tokens,
                "total_tokens": event.total_tokens,
                "response_source": event.response_source,
                "created_at": event.created_at,
            }
            for event, contact in recent_rows
        ],
        "quotas": [
            {
                "contact_id": quota.contact_id,
                "whatsapp_id": contact.whatsapp_id,
                "display_name": contact.display_name,
                "usage_count": quota.usage_count,
                "reset_time": quota.reset_time,
                "updated_at": quota.updated_at,
            }
            for quota, contact in quota_rows
        ],
    }


@router.get("/internet-usage")
async def internet_usage_dashboard(
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = today_start.replace(day=1)

    today_stats = await _internet_usage_totals(db, today_start)
    month_stats = await _internet_usage_totals(db, month_start)
    cache_count = (await db.execute(select(func.count(InternetCache.id)))).scalar_one()

    top_rows = (
        await db.execute(
            select(
                Contact.id,
                Contact.whatsapp_id,
                Contact.display_name,
                func.count(InternetUsageEvent.id).label("requests"),
            )
            .join(Contact, Contact.id == InternetUsageEvent.contact_id)
            .where(InternetUsageEvent.created_at >= month_start)
            .group_by(Contact.id, Contact.whatsapp_id, Contact.display_name)
            .order_by(func.count(InternetUsageEvent.id).desc())
            .limit(10)
        )
    ).all()

    service_rows = (
        await db.execute(
            select(InternetUsageEvent.service, func.count(InternetUsageEvent.id))
            .where(InternetUsageEvent.created_at >= month_start)
            .group_by(InternetUsageEvent.service)
            .order_by(func.count(InternetUsageEvent.id).desc())
        )
    ).all()

    recent_rows = (
        await db.execute(
            select(InternetUsageEvent, Contact)
            .outerjoin(Contact, Contact.id == InternetUsageEvent.contact_id)
            .order_by(InternetUsageEvent.created_at.desc())
            .limit(limit)
        )
    ).all()

    return {
        "today": today_stats,
        "month": month_stats,
        "cache_entries": cache_count,
        "top_users": [
            {
                "contact_id": contact_id,
                "whatsapp_id": whatsapp_id,
                "display_name": display_name,
                "requests": int(requests or 0),
            }
            for contact_id, whatsapp_id, display_name, requests in top_rows
        ],
        "services": [{"service": service, "requests": int(count or 0)} for service, count in service_rows],
        "recent": [
            {
                "id": event.id,
                "contact_id": event.contact_id,
                "whatsapp_id": contact.whatsapp_id if contact else "",
                "display_name": contact.display_name if contact else None,
                "service": event.service,
                "query_text": event.query_text,
                "provider": event.provider,
                "cache_hit": event.cache_hit,
                "success": event.success,
                "error_message": event.error_message,
                "created_at": event.created_at,
            }
            for event, contact in recent_rows
        ],
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
            details_json={
                "filename": filename,
                "entries": count,
                "path": str(CORE_FAQ_PATH),
                "refresh": _knowledge_refresh_targets(),
            },
        )
    )
    await db.commit()
    return {"ok": True, "entries": count, "path": str(CORE_FAQ_PATH), "refresh": _knowledge_refresh_targets()}


def _knowledge_refresh_targets() -> list[str]:
    return [
        "identity_engine",
        "help_engine",
        "project_responses",
        "command_help",
        "router_faq_index",
        "semantic_search_index",
        "conversation_engine",
        "project_intelligence",
        "ai_router_analytics",
    ]


async def _ai_usage_totals(db: AsyncSession, since) -> dict[str, int]:
    row = (
        await db.execute(
            select(
                func.count(AIUsageEvent.id),
                func.coalesce(func.sum(AIUsageEvent.prompt_tokens), 0),
                func.coalesce(func.sum(AIUsageEvent.completion_tokens), 0),
                func.coalesce(func.sum(AIUsageEvent.total_tokens), 0),
            ).where(AIUsageEvent.created_at >= since)
        )
    ).one()
    ai_calls, prompt_tokens, completion_tokens, total_tokens = row
    return {
        "ai_calls": int(ai_calls or 0),
        "prompt_tokens": int(prompt_tokens or 0),
        "completion_tokens": int(completion_tokens or 0),
        "total_tokens": int(total_tokens or 0),
    }


async def _internet_usage_totals(db: AsyncSession, since) -> dict[str, int]:
    requests = (
        await db.execute(select(func.count(InternetUsageEvent.id)).where(InternetUsageEvent.created_at >= since))
    ).scalar_one()
    cache_hits = (
        await db.execute(
            select(func.count(InternetUsageEvent.id))
            .where(InternetUsageEvent.created_at >= since)
            .where(InternetUsageEvent.cache_hit.is_(True))
        )
    ).scalar_one()
    failures = (
        await db.execute(
            select(func.count(InternetUsageEvent.id))
            .where(InternetUsageEvent.created_at >= since)
            .where(InternetUsageEvent.success.is_(False))
        )
    ).scalar_one()
    return {"requests": int(requests or 0), "cache_hits": int(cache_hits or 0), "failures": int(failures or 0)}


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
        "display_name": mem.display_name or contact.display_name,
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
        "relationship_type": mem.relationship_type,
        "personality_notes": mem.personality_notes,
        "first_seen_at": mem.first_seen_at,
        "last_interaction_at": mem.last_interaction_at,
        "created_at": mem.created_at,
        "updated_at": mem.updated_at,
    }

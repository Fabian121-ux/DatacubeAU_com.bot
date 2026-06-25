from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_admin_session
from app.config import settings
from app.core.experience_formatter import WhatsAppMessageFormat
from app.core.message_normalizer import NormalizedMessage
from app.core.router import InboundRouter
from app.db import get_db_session
from app.models.enums import ChatType, DecisionType, GroupReplyMode
from app.models.schema import (
    AICall,
    AIUsageEvent,
    AIUsageQuota,
    AdminAccount,
    AuditLog,
    BotConfig,
    Contact,
    ConversationSession,
    ConversationSummary,
    ConversationTimeline,
    FAQEntry,
    GroupConfig,
    GroupMetadata,
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
from app.services.admin_management_service import AdminManagementService
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


class GroupConfigIn(BaseModel):
    chat_id: str
    display_name: str | None = None
    reply_mode: GroupReplyMode = GroupReplyMode.MENTION_ONLY
    is_enabled: bool = True
    cooldown_seconds: int = Field(default=45, ge=0, le=3600)


class GroupConfigUpdate(BaseModel):
    chat_id: str | None = None
    display_name: str | None = None
    reply_mode: GroupReplyMode | None = None
    is_enabled: bool | None = None
    cooldown_seconds: int | None = Field(default=None, ge=0, le=3600)


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


class AdminAccountIn(BaseModel):
    name: str
    whatsapp_number: str
    role: str = "admin"
    permission_level: str = "owner"
    is_primary: bool = False


class AdminAccountUpdate(BaseModel):
    name: str | None = None
    whatsapp_number: str | None = None
    role: str | None = None
    permission_level: str | None = None
    is_enabled: bool | None = None
    is_primary: bool | None = None


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
    is_enabled: bool | None = None


class MemoryFactIn(BaseModel):
    contact_id: int
    memory_text: str = Field(min_length=2, max_length=1200)
    memory_type: str = "profile_fact"
    source: str = "admin"
    importance: float = Field(default=0.5, ge=0.0, le=1.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    is_enabled: bool = True


class MemoryFactUpdate(BaseModel):
    memory_text: str | None = Field(default=None, min_length=2, max_length=1200)
    memory_type: str | None = None
    source: str | None = None
    importance: float | None = Field(default=None, ge=0.0, le=1.0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    is_enabled: bool | None = None


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
    contact_map: dict[int, Contact] = {}
    final_response_map: dict[int, str] = {}
    whatsapp_final_response_map: dict[int, str] = {}
    response_formatting_map: dict[int, dict[str, Any]] = {}
    if inbound_ids:
        inbound_messages = (
            await db.execute(select(Message).where(Message.id.in_(inbound_ids)))
        ).scalars().all()
        inbound_map = {message.id: message for message in inbound_messages}
        contact_ids = [message.contact_id for message in inbound_messages if message.contact_id]
        if contact_ids:
            contacts = (await db.execute(select(Contact).where(Contact.id.in_(contact_ids)))).scalars().all()
            contact_map = {contact.id: contact for contact in contacts}
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
                final_response_map[inbound.id] = _display_text_for_message(final)
                whatsapp_final_response_map[inbound.id] = final.message_text
                response_formatting_map[inbound.id] = _message_formatting(final)
    return {
        "count": len(rows),
        "items": [
            {
                "id": row[0].id,
                "message_id": row[0].message_id,
                "message": (inbound_map.get(row[0].message_id).message_text if inbound_map.get(row[0].message_id) else None),
                "user_name": (
                    contact_map.get(inbound_map[row[0].message_id].contact_id).display_name
                    if inbound_map.get(row[0].message_id)
                    and inbound_map[row[0].message_id].contact_id
                    and contact_map.get(inbound_map[row[0].message_id].contact_id)
                    else None
                ),
                "phone_number": (
                    contact_map.get(inbound_map[row[0].message_id].contact_id).normalized_phone
                    or contact_map.get(inbound_map[row[0].message_id].contact_id).whatsapp_phone
                    if inbound_map.get(row[0].message_id)
                    and inbound_map[row[0].message_id].contact_id
                    and contact_map.get(inbound_map[row[0].message_id].contact_id)
                    else None
                ),
                "whatsapp_id": (
                    contact_map.get(inbound_map[row[0].message_id].contact_id).whatsapp_id
                    if inbound_map.get(row[0].message_id)
                    and inbound_map[row[0].message_id].contact_id
                    and contact_map.get(inbound_map[row[0].message_id].contact_id)
                    else None
                ),
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
                "fallback_reason": ((audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("fallback") or {}).get("reason"),
                "identity_used": (audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("identity"),
                "memory_used": (audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("memory"),
                "faq_used": (audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("faq"),
                "knowledge_used": (audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("knowledge"),
                "project_context": (audit_map.get(str(row[0].id), {}).get("source_diagnostics") or {}).get("project"),
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
                "whatsapp_final_response": whatsapp_final_response_map.get(row[0].message_id),
                "response_formatting": response_formatting_map.get(row[0].message_id) or {},
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
                "display_text": _display_text_for_message(row),
                "whatsapp_formatted_text": row.message_text if row.direction == "outbound" else None,
                "formatting": _message_formatting(row),
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
        display_reply_text = planned.raw_reply_text or planned.reply_text
        return {
            "decision_type": planned.decision_type.value,
            "source": planned.source_diagnostics.get("source"),
            "reason": planned.reason,
            "should_reply": planned.should_reply,
            "reply_text": display_reply_text,
            "display_reply_text": display_reply_text,
            "raw_reply_text": planned.raw_reply_text,
            "whatsapp_reply_text": planned.reply_text,
            "response_formatting": planned.source_diagnostics.get("experience", {}),
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
    chat_type_filter = payload.chat_type_filter if payload.chat_type_filter != "" else None
    rule = await _find_reply_rule_by_key(db, payload.keyword, payload.match_mode, chat_type_filter)
    created = rule is None
    if rule is None:
        rule = ReplyRule(
            keyword=payload.keyword,
            response_text=payload.response_text,
            match_mode=payload.match_mode,
            chat_type_filter=chat_type_filter,
            is_enabled=payload.is_enabled,
            priority=payload.priority,
            updated_at=utcnow(),
        )
        db.add(rule)
    else:
        rule.keyword = payload.keyword
        rule.response_text = payload.response_text
        rule.match_mode = payload.match_mode
        rule.chat_type_filter = chat_type_filter
        rule.is_enabled = payload.is_enabled
        rule.priority = payload.priority
        rule.updated_at = utcnow()
    db.add(
        AuditLog(
            action="reply_rule_created" if created else "reply_rule_updated",
            entity_type="reply_rule",
            entity_id=str(rule.id) if rule.id else None,
            details_json=payload.model_dump(),
        )
    )
    await db.commit()
    await db.refresh(rule)
    return {"ok": True, "id": rule.id, "created": created}


@router.put("/reply-rules/{rule_id}")
async def update_reply_rule(
    rule_id: int,
    payload: ReplyRuleUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    rule = await db.get(ReplyRule, rule_id)
    if not rule:
        raise HTTPException(status_code=404, detail="rule not found")
    next_keyword = payload.keyword if payload.keyword is not None else rule.keyword
    next_match_mode = payload.match_mode if payload.match_mode is not None else rule.match_mode
    if payload.chat_type_filter is not None:
        next_chat_type_filter = payload.chat_type_filter if payload.chat_type_filter != "" else None
    else:
        next_chat_type_filter = rule.chat_type_filter
    duplicate = await _find_reply_rule_by_key(
        db,
        next_keyword,
        next_match_mode,
        next_chat_type_filter,
        exclude_id=rule_id,
    )
    if duplicate:
        raise HTTPException(status_code=409, detail=f"duplicate reply rule exists: {duplicate.id}")
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
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = select(GroupConfig).order_by(GroupConfig.updated_at.desc()).limit(limit)
    if status == "enabled":
        stmt = stmt.where(GroupConfig.is_enabled.is_(True))
    elif status == "disabled":
        stmt = stmt.where(GroupConfig.is_enabled.is_(False))
    if q:
        like = f"%{q}%"
        stmt = stmt.where(or_(GroupConfig.chat_id.ilike(like), GroupConfig.display_name.ilike(like)))
    rows = (await db.execute(stmt)).scalars().all()
    metadata_rows = (
        await db.execute(select(GroupMetadata).where(GroupMetadata.chat_id.in_([row.chat_id for row in rows])))
    ).scalars().all() if rows else []
    metadata_by_chat = {row.chat_id: row for row in metadata_rows}
    return {
        "count": len(rows),
        "items": [
            {
                "id": r.id,
                "chat_id": r.chat_id,
                "display_name": r.display_name or getattr(metadata_by_chat.get(r.chat_id), "group_name", None) or r.chat_id,
                "configured_display_name": r.display_name,
                "waha_group_name": getattr(metadata_by_chat.get(r.chat_id), "group_name", None),
                "reply_mode": r.reply_mode,
                "is_enabled": r.is_enabled,
                "enabled": r.is_enabled,
                "cooldown_seconds": r.cooldown_seconds,
                "created_at": getattr(r, "created_at", None),
                "updated_at": r.updated_at,
            }
            for r in rows
        ],
    }


@router.post("/groups")
async def create_group_config(
    payload: GroupConfigIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    chat_id = payload.chat_id.strip()
    if not chat_id:
        raise HTTPException(status_code=400, detail="chat_id is required")
    existing = (await db.execute(select(GroupConfig).where(GroupConfig.chat_id == chat_id).limit(1))).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="group chat_id already exists")
    row = GroupConfig(
        chat_id=chat_id,
        display_name=payload.display_name,
        reply_mode=payload.reply_mode.value,
        is_enabled=payload.is_enabled,
        cooldown_seconds=payload.cooldown_seconds,
        updated_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    db.add(AuditLog(action="group_config_created", entity_type="group_config", entity_id=str(row.id), details_json=payload.model_dump(mode="json")))
    await db.commit()
    return {"ok": True, "id": row.id}


@router.put("/groups/{group_id}")
async def update_group_config(
    group_id: int,
    payload: GroupConfigUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = await db.get(GroupConfig, group_id)
    if not row:
        raise HTTPException(status_code=404, detail="group not found")
    updates = payload.model_dump(exclude_unset=True, mode="json")
    new_chat_id = updates.get("chat_id")
    if new_chat_id and new_chat_id != row.chat_id:
        duplicate = (await db.execute(select(GroupConfig).where(GroupConfig.chat_id == new_chat_id).limit(1))).scalar_one_or_none()
        if duplicate:
            raise HTTPException(status_code=409, detail="group chat_id already exists")
        row.chat_id = new_chat_id
    if "display_name" in updates:
        row.display_name = updates["display_name"]
    if "reply_mode" in updates and updates["reply_mode"] is not None:
        row.reply_mode = str(updates["reply_mode"])
    if "is_enabled" in updates and updates["is_enabled"] is not None:
        row.is_enabled = updates["is_enabled"]
    if "cooldown_seconds" in updates and updates["cooldown_seconds"] is not None:
        row.cooldown_seconds = int(updates["cooldown_seconds"])
    row.updated_at = utcnow()
    db.add(AuditLog(action="group_config_updated", entity_type="group_config", entity_id=str(row.id), details_json=updates))
    await db.commit()
    return {"ok": True, "id": row.id}


@router.delete("/groups/{group_id}")
async def delete_group_config(
    group_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = await db.get(GroupConfig, group_id)
    if not row:
        raise HTTPException(status_code=404, detail="group not found")
    await db.delete(row)
    db.add(AuditLog(action="group_config_deleted", entity_type="group_config", entity_id=str(group_id), details_json={"group_id": group_id}))
    await db.commit()
    return {"ok": True, "id": group_id}


# ---------------------------------------------------------------------------
# Memory Management
# ---------------------------------------------------------------------------

@router.get("/memory")
async def list_memory(
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(UserMemory, Contact)
        .join(Contact, Contact.id == UserMemory.contact_id)
        .order_by(UserMemory.updated_at.desc())
        .limit(limit)
    )
    if status == "enabled":
        stmt = stmt.where(UserMemory.is_enabled.is_(True))
    elif status == "disabled":
        stmt = stmt.where(UserMemory.is_enabled.is_(False))
    if q:
        like = f"%{q}%"
        norm_like = f"%{normalize_text(q)}%"
        stmt = stmt.where(
            or_(
                Contact.display_name.ilike(like),
                Contact.whatsapp_id.ilike(like),
                Contact.normalized_phone.ilike(like),
                UserMemory.display_name.ilike(like),
                UserMemory.user_name.ilike(like),
                UserMemory.interests.ilike(norm_like),
                UserMemory.projects.ilike(norm_like),
            )
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
                "enabled": mem.is_enabled,
                "is_enabled": mem.is_enabled,
                "usage_count": mem.usage_count,
                "last_used_at": mem.last_used_at,
                "first_seen_at": mem.first_seen_at,
                "last_interaction_at": mem.last_interaction_at,
                "created_at": mem.created_at,
                "updated_at": mem.updated_at,
            }
            for mem, contact in rows
        ],
    }


@router.get("/memory/facts")
async def list_memory_facts(
    q: str | None = Query(default=None),
    contact_id: int | None = Query(default=None),
    memory_type: str | None = Query(default=None),
    status: str | None = Query(default=None),
    min_importance: float | None = Query(default=None, ge=0.0, le=1.0),
    limit: int = Query(default=100, ge=1, le=300),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    stmt = (
        select(UserMemoryTimeline, Contact)
        .join(Contact, Contact.id == UserMemoryTimeline.contact_id)
        .order_by(UserMemoryTimeline.updated_at.desc())
        .limit(limit)
    )
    if contact_id is not None:
        stmt = stmt.where(UserMemoryTimeline.contact_id == contact_id)
    if memory_type:
        stmt = stmt.where(UserMemoryTimeline.memory_type == memory_type)
    if status == "enabled":
        stmt = stmt.where(UserMemoryTimeline.is_enabled.is_(True))
    elif status == "disabled":
        stmt = stmt.where(UserMemoryTimeline.is_enabled.is_(False))
    if min_importance is not None:
        stmt = stmt.where(UserMemoryTimeline.importance >= min_importance)
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                UserMemoryTimeline.memory_text.ilike(like),
                Contact.display_name.ilike(like),
                Contact.whatsapp_id.ilike(like),
                Contact.normalized_phone.ilike(like),
            )
        )
    rows = (await db.execute(stmt)).all()
    return {
        "count": len(rows),
        "items": [_memory_fact_payload(row, contact) for row, contact in rows],
    }


@router.post("/memory/facts")
async def create_memory_fact(
    payload: MemoryFactIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    contact = await db.get(Contact, payload.contact_id)
    if not contact:
        raise HTTPException(status_code=404, detail="contact not found")
    normalized = normalize_text(payload.memory_text)
    existing_rows = (
        await db.execute(
            select(UserMemoryTimeline)
            .where(UserMemoryTimeline.contact_id == payload.contact_id)
            .where(UserMemoryTimeline.is_enabled.is_(True))
        )
    ).scalars().all()
    if any(normalize_text(row.memory_text) == normalized for row in existing_rows):
        raise HTTPException(status_code=409, detail="duplicate memory fact for this user")
    row = UserMemoryTimeline(
        contact_id=payload.contact_id,
        memory_text=payload.memory_text.strip(),
        source=payload.source[:40],
        memory_type=payload.memory_type[:40],
        importance=payload.importance,
        confidence=payload.confidence,
        is_enabled=payload.is_enabled,
        updated_at=utcnow(),
    )
    db.add(row)
    await db.flush()
    db.add(AuditLog(action="memory_fact_created", entity_type="user_memory_timeline", entity_id=str(row.id), details_json=payload.model_dump()))
    await db.commit()
    return {"ok": True, "item": _memory_fact_payload(row, contact)}


@router.put("/memory/facts/{fact_id}")
async def update_memory_fact(
    fact_id: int,
    payload: MemoryFactUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = await db.get(UserMemoryTimeline, fact_id)
    if not row:
        raise HTTPException(status_code=404, detail="memory fact not found")
    updates = payload.model_dump(exclude_unset=True)
    if "memory_text" in updates and updates["memory_text"] is not None:
        row.memory_text = str(updates["memory_text"]).strip()
    for field in ("memory_type", "source"):
        if field in updates and updates[field] is not None:
            setattr(row, field, str(updates[field])[:40])
    for field in ("importance", "confidence", "is_enabled"):
        if field in updates and updates[field] is not None:
            setattr(row, field, updates[field])
    row.updated_at = utcnow()
    contact = await db.get(Contact, row.contact_id)
    db.add(AuditLog(action="memory_fact_updated", entity_type="user_memory_timeline", entity_id=str(row.id), details_json=updates))
    await db.commit()
    return {"ok": True, "item": _memory_fact_payload(row, contact)}


@router.delete("/memory/facts/{fact_id}")
async def delete_memory_fact(
    fact_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    row = await db.get(UserMemoryTimeline, fact_id)
    if not row:
        raise HTTPException(status_code=404, detail="memory fact not found")
    contact_id = row.contact_id
    await db.delete(row)
    db.add(AuditLog(action="memory_fact_deleted", entity_type="user_memory_timeline", entity_id=str(fact_id), details_json={"contact_id": contact_id}))
    await db.commit()
    return {"ok": True, "id": fact_id, "contact_id": contact_id}


@router.get("/memory/export")
async def export_memory(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    profiles = (await db.execute(select(UserMemory, Contact).join(Contact, Contact.id == UserMemory.contact_id))).all()
    facts = (await db.execute(select(UserMemoryTimeline, Contact).join(Contact, Contact.id == UserMemoryTimeline.contact_id))).all()
    return {
        "profiles": [_profile_payload(mem, contact) for mem, contact in profiles],
        "facts": [_memory_fact_payload(row, contact) for row, contact in facts],
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
    if payload.is_enabled is not None:
        mem.is_enabled = payload.is_enabled
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
            "memory_type": getattr(row, "memory_type", "profile_fact"),
            "importance_score": getattr(row, "importance", None) or row.confidence,
            "confidence": row.confidence,
            "enabled": bool(getattr(row, "is_enabled", True)),
            "is_enabled": bool(getattr(row, "is_enabled", True)),
            "usage_count": int(getattr(row, "usage_count", 0) or 0),
            "last_used_at": getattr(row, "last_used_at", None),
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
    entity_type = "conversation_timeline"
    if not deleted:
        result = await db.execute(
            delete(UserMemoryTimeline)
            .where(UserMemoryTimeline.id == timeline_id)
            .where(UserMemoryTimeline.contact_id == contact_id)
        )
        deleted = bool(result.rowcount)
        entity_type = "user_memory_timeline"
    if not deleted:
        raise HTTPException(status_code=404, detail="timeline entry not found for this contact")
    db.add(
        AuditLog(
            action=f"{entity_type}_deleted",
            entity_type=entity_type,
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
        select(Contact, UserMemory)
        .outerjoin(UserMemory, UserMemory.contact_id == Contact.id)
        .order_by(Contact.last_active_at.desc().nulls_last(), Contact.updated_at.desc())
        .limit(limit)
    )
    if q:
        like = f"%{normalize_text(q)}%"
        display_like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Contact.whatsapp_id.ilike(display_like),
                Contact.display_name.ilike(display_like),
                Contact.push_name.ilike(display_like),
                Contact.contact_name.ilike(display_like),
                Contact.normalized_phone.ilike(display_like),
                Contact.chat_id.ilike(display_like),
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
    items = []
    for contact, mem in rows:
        payload = _profile_payload(mem, contact)
        payload["message_count"] = int(
            (await db.execute(select(func.count(Message.id)).where(Message.contact_id == contact.id))).scalar_one() or 0
        )
        payload["memory_count"] = int(
            (await db.execute(select(func.count(UserMemoryTimeline.id)).where(UserMemoryTimeline.contact_id == contact.id))).scalar_one() or 0
        )
        session = (
            await db.execute(select(ConversationSession).where(ConversationSession.chat_id == contact.whatsapp_id).limit(1))
        ).scalar_one_or_none()
        payload["current_conversation_mode"] = "global" if getattr(mem, "global_chat_enabled", False) else "standard"
        payload["last_intent"] = getattr(session, "last_intent", None)
        items.append(payload)
    return {
        "count": len(items),
        "items": items,
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
            contact.is_name_verified = True
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
    value = payload.value
    if payload.key == "whatsapp_message_format":
        try:
            value = WhatsAppMessageFormat(payload.value.strip().lower()).value
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="whatsapp_message_format must be standard, quote, or automatic") from exc
    await svc.set(payload.key, value)
    db.add(AuditLog(action="config_updated", entity_type="bot_config", entity_id=payload.key, details_json={"value": value}))
    await db.commit()
    return {"ok": True, "key": payload.key, "value": value}


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
    await IdentityRegistryService(db).ensure_defaults_from_profile(identity)
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
    service = FAQService(db)
    source_version = service.version_for_text(content)
    rows = (
        await db.execute(
            select(FAQEntry)
            .where(FAQEntry.source_id == "core_faq")
            .where(FAQEntry.source_version == source_version)
            .where(FAQEntry.is_enabled.is_(True))
            .order_by(FAQEntry.id)
        )
    ).scalars().all()
    analytics = await service.analytics()
    preview = await service.preview_source(content)
    return {
        "path": str(CORE_FAQ_PATH),
        "content": content,
        "source_id": "core_faq",
        "source_version": source_version,
        "parse_status": preview["parse_status"],
        "sync_status": "synced" if len(rows) == preview["entry_count"] else "out_of_sync",
        "count": len(rows),
        "items": [service.serialize_entry(row) for row in rows],
        "preview": preview,
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


@router.post("/faq/replace")
async def replace_faq(
    payload: FAQSaveIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    return await _save_and_sync_faq(payload.content, db, action="faq_replaced", filename=None)


@router.post("/faq/reparse")
async def reparse_faq(
    payload: FAQSaveIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="FAQ content is empty")
    preview = await FAQService(db).preview_source(payload.content)
    return {"ok": True, **preview}


@router.post("/faq/resync")
async def resync_faq(
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    content = CORE_FAQ_PATH.read_text(encoding="utf-8") if CORE_FAQ_PATH.exists() else ""
    return await _save_and_sync_faq(content, db, action="faq_resynced", filename=CORE_FAQ_PATH.name)


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


@router.get("/commands/available")
async def available_commands(
    permission: str = Query(default="user", pattern="^(user|owner)$"),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = CommandCatalogService(db)
    items = [
        item
        for item in await service.list_commands()
        if item["enabled"] and (item["permissions"] == "user" or permission == "owner")
    ]
    sections: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        sections.setdefault(item["category"], []).append(item)
    return {"count": len(items), "permission": permission, "sections": sections, "items": items}


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


@router.get("/admins")
async def list_admin_accounts(
    q: str | None = Query(default=None),
    role: str | None = Query(default=None),
    status: str | None = Query(default=None),
    include_disabled: bool = Query(default=True),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    await service.ensure_from_config()
    rows = await service.list_admins(include_disabled=include_disabled, search=q)
    if role:
        rows = [row for row in rows if (row.role or "").lower() == role.lower()]
    if status == "enabled":
        rows = [row for row in rows if row.is_enabled]
    if status == "disabled":
        rows = [row for row in rows if not row.is_enabled]
    total = len(rows)
    rows = rows[offset : offset + limit]
    await db.commit()
    return {"count": total, "limit": limit, "offset": offset, "items": [service.serialize(row) for row in rows]}


@router.post("/admins")
async def create_admin_account(
    payload: AdminAccountIn,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    await service.ensure_from_config()
    try:
        row = await service.create_admin(
            name=payload.name,
            whatsapp_number=payload.whatsapp_number,
            role=payload.role,
            permission_level=payload.permission_level,
            is_primary=payload.is_primary,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="admin_account_created",
            entity_type="admin_account",
            entity_id=str(row.id),
            details_json=service.serialize(row),
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize(row)}


@router.put("/admins/{admin_id}")
async def update_admin_account(
    admin_id: int,
    payload: AdminAccountUpdate,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    try:
        row = await service.update_admin(admin_id, payload.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="admin_account_updated",
            entity_type="admin_account",
            entity_id=str(row.id),
            details_json=payload.model_dump(exclude_unset=True),
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize(row)}


@router.post("/admins/{admin_id}/enable")
async def set_admin_enabled(
    admin_id: int,
    payload: dict[str, bool],
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    try:
        row = await service.set_enabled(admin_id, bool(payload.get("enabled", True)))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="admin_account_enabled_changed",
            entity_type="admin_account",
            entity_id=str(row.id),
            details_json={"enabled": row.is_enabled},
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize(row)}


@router.post("/admins/{admin_id}/primary")
async def set_primary_admin(
    admin_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    try:
        row = await service.set_primary(admin_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="admin_account_primary_set",
            entity_type="admin_account",
            entity_id=str(row.id),
            details_json={"primary": True},
        )
    )
    await db.commit()
    return {"ok": True, "item": service.serialize(row)}


@router.delete("/admins/{admin_id}")
async def delete_admin_account(
    admin_id: int,
    db: AsyncSession = Depends(get_db_session),
) -> dict[str, Any]:
    service = AdminManagementService(db)
    try:
        row = await service.delete_admin(admin_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.add(
        AuditLog(
            action="admin_account_deleted",
            entity_type="admin_account",
            entity_id=str(admin_id),
            details_json=service.serialize(row),
        )
    )
    await db.commit()
    return {"ok": True}


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
    service = FAQService(db)
    pairs = service.parse_faq_text(content)
    if not pairs:
        raise HTTPException(status_code=400, detail="FAQ content has no parseable question and answer entries")
    source_version = service.version_for_text(content)
    sync_report = await service.replace_source_entries_report(
        pairs,
        source_id="core_faq",
        source_name=filename or CORE_FAQ_PATH.name,
        source_version=source_version,
    )
    cache_result = await db.execute(
        delete(QACache).where(QACache.answer_mode.in_([DecisionType.FAQ_REPLY.value, DecisionType.KB_REPLY.value]))
    )
    cache_rows_deleted = int(cache_result.rowcount or 0)
    CORE_FAQ_PATH.write_text(content, encoding="utf-8")
    db.add(
        AuditLog(
            action=action,
            entity_type="faq_entries",
            entity_id=None,
            details_json={
                "filename": filename,
                "entries": sync_report["active_entries"],
                "sync_report": sync_report,
                "cache_rows_deleted": cache_rows_deleted,
                "path": str(CORE_FAQ_PATH),
                "source_id": "core_faq",
                "source_version": source_version,
                "parse_status": "ok",
                "sync_status": "synced",
                "refresh": _knowledge_refresh_targets(),
            },
        )
    )
    await db.commit()
    return {
        "ok": True,
        "entries": sync_report["active_entries"],
        "sync_report": sync_report,
        "created": sync_report["created"],
        "updated": sync_report["updated"],
        "superseded": sync_report["superseded"],
        "disabled": sync_report["disabled"],
        "duplicates": sync_report["duplicates"],
        "active_entries": sync_report["active_entries"],
        "cache_rows_deleted": cache_rows_deleted,
        "path": str(CORE_FAQ_PATH),
        "source_id": "core_faq",
        "source_version": source_version,
        "parse_status": "ok",
        "save_status": "saved",
        "sync_status": "synced",
        "index_status": "refresh_requested",
        "refresh": _knowledge_refresh_targets(),
    }


async def _find_reply_rule_by_key(
    db: AsyncSession,
    keyword: str,
    match_mode: str,
    chat_type_filter: str | None,
    *,
    exclude_id: int | None = None,
) -> ReplyRule | None:
    normalized_keyword = normalize_text(keyword)
    rows = (await db.execute(select(ReplyRule))).scalars().all()
    for row in rows:
        if exclude_id is not None and row.id == exclude_id:
            continue
        if normalize_text(row.keyword) != normalized_keyword:
            continue
        if row.match_mode != match_mode:
            continue
        if (row.chat_type_filter or None) != (chat_type_filter or None):
            continue
        return row
    return None


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
        "display_text": _display_text_from_formatting(row.message_text, row.formatting_json),
        "formatting": row.formatting_json or {},
        "status": row.status,
        "retry_count": row.retry_count,
        "max_retries": row.max_retries,
        "next_attempt_at": row.next_attempt_at,
        "error_message": row.error_message,
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


def _message_formatting(row: Message) -> dict[str, Any]:
    payload = row.raw_payload_json if isinstance(row.raw_payload_json, dict) else {}
    formatting = payload.get("formatting")
    return formatting if isinstance(formatting, dict) else {}


def _display_text_for_message(row: Message) -> str:
    payload = row.raw_payload_json if isinstance(row.raw_payload_json, dict) else {}
    raw_reply_text = payload.get("raw_reply_text")
    if row.direction == "outbound" and isinstance(raw_reply_text, str) and raw_reply_text.strip():
        return raw_reply_text
    return row.message_text


def _display_text_from_formatting(final_text: str, formatting: dict[str, Any] | None) -> str:
    if isinstance(formatting, dict):
        raw_reply_text = formatting.get("raw_reply_text")
        if isinstance(raw_reply_text, str) and raw_reply_text.strip():
            return raw_reply_text
    return final_text


def _profile_payload(mem: UserMemory | None, contact: Contact) -> dict[str, Any]:
    verified_display_name = contact.display_name if bool(getattr(contact, "is_name_verified", False)) else None
    display_name = (
        verified_display_name
        or getattr(contact, "contact_name", None)
        or getattr(contact, "push_name", None)
        or getattr(mem, "display_name", None)
        or getattr(contact, "display_name", None)
        or getattr(contact, "normalized_phone", None)
        or contact.whatsapp_id
    )
    return {
        "id": getattr(mem, "id", None),
        "contact_id": contact.id,
        "whatsapp_id": contact.whatsapp_id,
        "display_name": display_name,
        "verified_manual_name": bool(getattr(contact, "is_name_verified", False)),
        "whatsapp_display_name": contact.display_name,
        "whatsapp_push_name": getattr(contact, "push_name", None),
        "whatsapp_contact_name": getattr(contact, "contact_name", None),
        "phone_number": getattr(contact, "whatsapp_phone", None),
        "normalized_phone": getattr(contact, "normalized_phone", None),
        "chat_id": getattr(contact, "chat_id", None),
        "waha_contact_id": getattr(contact, "waha_contact_id", None),
        "waha_participant_id": getattr(contact, "waha_participant_id", None),
        "profile_image_url": getattr(contact, "profile_image_url", None),
        "identity_source": getattr(contact, "identity_source", None),
        "identity_json": getattr(contact, "identity_json", None) or {},
        "enabled": True,
        "user_name": getattr(mem, "user_name", None),
        "preferences": getattr(mem, "preferences", None),
        "context_notes": getattr(mem, "context_notes", None),
        "onboarding_complete": bool(getattr(mem, "onboarding_complete", False)) if mem else False,
        "profession": getattr(mem, "profession", None),
        "interests": getattr(mem, "interests", None),
        "projects": getattr(mem, "projects", None),
        "goals": getattr(mem, "goals", None),
        "communication_style": getattr(mem, "communication_style", None),
        "relationship": getattr(mem, "relationship", None),
        "relationship_type": getattr(mem, "relationship_type", "unknown") if mem else "unknown",
        "personality_notes": getattr(mem, "personality_notes", None),
        "first_seen_at": getattr(mem, "first_seen_at", None) or contact.created_at,
        "last_interaction_at": getattr(mem, "last_interaction_at", None) or contact.last_active_at,
        "created_at": getattr(mem, "created_at", None) or contact.created_at,
        "updated_at": getattr(mem, "updated_at", None) or contact.updated_at,
    }


def _memory_fact_payload(row: UserMemoryTimeline, contact: Contact | None = None) -> dict[str, Any]:
    return {
        "id": row.id,
        "contact_id": row.contact_id,
        "user_name": getattr(contact, "display_name", None) if contact else None,
        "whatsapp_id": getattr(contact, "whatsapp_id", None) if contact else None,
        "normalized_phone": getattr(contact, "normalized_phone", None) if contact else None,
        "memory_text": row.memory_text,
        "source": row.source,
        "memory_type": getattr(row, "memory_type", "profile_fact"),
        "importance": float(getattr(row, "importance", 0.5) or 0.0),
        "confidence": float(getattr(row, "confidence", 1.0) or 0.0),
        "enabled": bool(getattr(row, "is_enabled", True)),
        "is_enabled": bool(getattr(row, "is_enabled", True)),
        "usage_count": int(getattr(row, "usage_count", 0) or 0),
        "last_used_at": getattr(row, "last_used_at", None),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }

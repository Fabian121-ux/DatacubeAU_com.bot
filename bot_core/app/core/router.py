from __future__ import annotations

import asyncio
from dataclasses import asdict, dataclass
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.message_normalizer import MessageNormalizer, NormalizedMessage
from app.core.reply_planner import PlannedReply, ReplyPlanner
from app.models.enums import DecisionType, Direction
from app.models.schema import AuditLog, Contact, Message, OutboundMessage, RouterDecision
from app.services.logging_service import log_event
from app.services.owner_command_service import OwnerCommandService
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.text import normalize_text
from app.utils.time import utcnow


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class RouteResult:
    status: str
    chat_type: str
    action: str
    decision_type: str
    reason: str
    kb_confidence: float
    inbound_message_id: int
    outbound_message_id: int | None
    outbound_queue_id: int | None = None
    delivery_error: str | None = None


class InboundRouter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.normalizer = MessageNormalizer()
        self.reply_planner = ReplyPlanner(session)

    async def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalizer.normalize(event)
        contact = await self._get_or_create_contact(normalized.sender_id, normalized.sender_name)
        inbound = await self._save_inbound_message(normalized, contact.id)
        await self.reply_planner.memory_service.ensure_relationship_profile(
            contact.id,
            normalized.sender_name or contact.display_name,
        )
        await self._save_audit_log(
            action="inbound_received",
            entity_type="message",
            entity_id=str(inbound.id),
            details_json={
                "chat_id": normalized.chat_id,
                "chat_type": normalized.chat_type.value,
                "message_type": normalized.message_type,
                "is_bot_mentioned": normalized.is_bot_mentioned,
            },
        )
        log_event(
            logger,
            logging.INFO,
            "inbound_received",
            message_id=inbound.id,
            chat_id=normalized.chat_id,
            chat_type=normalized.chat_type.value,
        )

        owner_command = await OwnerCommandService(self.session).handle(normalized, contact)
        if owner_command:
            planned = await self.reply_planner._apply_identity_guard(
                PlannedReply(
                    decision_type=DecisionType.STATIC_REPLY,
                    reason=f"owner command: {owner_command.command}",
                    should_reply=True,
                    reply_text=owner_command.reply_text,
                    source_diagnostics=owner_command.source_diagnostics,
                )
        )
        else:
            profile_facts = await self.reply_planner.memory_service.extract_profile_from_message(
                contact.id,
                normalized.message_text,
            )
            if profile_facts:
                await self._save_audit_log(
                    action="memory_profile_extracted",
                    entity_type="contact",
                    entity_id=str(contact.id),
                    details_json={"facts": profile_facts},
                )

            typing_started = await self._maybe_start_typing(normalized.chat_id)
            planned = await self.reply_planner.plan(normalized, contact.id)
            if typing_started:
                await self._maybe_stop_typing(normalized.chat_id)
        self._attach_thinking_diagnostics(planned)
        decision = await self._save_router_decision(
            message_id=inbound.id,
            decision_type=planned.decision_type.value,
            reason=planned.reason,
            confidence=planned.kb_confidence,
            reply_sent=False,
        )
        await self._save_audit_log(
            action="router_decision",
            entity_type="router_decision",
            entity_id=str(decision.id),
            details_json={
                "message_id": inbound.id,
                "decision_type": planned.decision_type.value,
                "reason": planned.reason,
                "kb_confidence": planned.kb_confidence,
                "should_reply": planned.should_reply,
            },
        )
        log_event(
            logger,
            logging.INFO,
            "router_decision",
            message_id=inbound.id,
            decision_type=planned.decision_type.value,
            should_reply=planned.should_reply,
            kb_confidence=planned.kb_confidence,
        )
        if not planned.should_reply or not planned.reply_text:
            await self.session.commit()
            return asdict(RouteResult(
                status="ok",
                chat_type=normalized.chat_type.value,
                action="ignored",
                decision_type=planned.decision_type.value,
                reason=planned.reason,
                kb_confidence=planned.kb_confidence,
                inbound_message_id=inbound.id,
                outbound_message_id=None,
            ))

        await self._maybe_typing_delay(normalized, planned)
        queued = await self._queue_outbound_message(
            normalized.chat_id,
            planned.reply_text,
            media_url=planned.media_url,
            media_type=planned.media_type,
            media_caption=planned.media_caption,
        )
        outbound = await self._save_outbound_message(normalized, contact.id, planned.reply_text, queued.id)
        decision.reply_sent = True
        if planned.ai_call:
            planned.ai_call.message_id = inbound.id
            self.session.add(planned.ai_call)
            await self.session.flush()
            usage_event = await self.reply_planner.rate_limiter.record_ai_usage(
                contact.id,
                planned.ai_call,
                response_source=str(planned.source_diagnostics.get("source") or "AI"),
            )
            planned.source_diagnostics.setdefault("ai_usage", {})["event_id"] = usage_event.id
            planned.source_diagnostics["ai_usage"]["total_tokens"] = usage_event.total_tokens
        await self.reply_planner.cache_answer_if_reusable(normalized.message_text, planned)
        await self.reply_planner.upsert_conversation_summary(
            chat_id=normalized.chat_id,
            chat_type=normalized.chat_type.value,
            user_text=normalized.message_text,
            bot_text=planned.reply_text,
            decision=planned.decision_type.value,
        )
        timeline_entry = await self.reply_planner.memory_service.log_conversation_event(
            contact.id,
            user_text=normalized.message_text,
            decision=planned.decision_type.value,
        )
        threshold_config = await self.reply_planner.bot_config.get("memory_summary_thresholds", "25,50,100")
        due_summaries = await self.reply_planner.memory_service.generate_due_summaries(
            contact.id,
            chat_id=normalized.chat_id,
            thresholds=self.reply_planner.memory_service.parse_summary_thresholds(threshold_config),
        )
        if timeline_entry:
            await self._save_audit_log(
                action="conversation_timeline_created",
                entity_type="conversation_timeline",
                entity_id=str(timeline_entry.id),
                details_json={
                    "contact_id": contact.id,
                    "topic": timeline_entry.topic,
                    "source": timeline_entry.source,
                    "importance_score": timeline_entry.importance_score,
                },
            )
        if due_summaries:
            await self._save_audit_log(
                action="conversation_summaries_created",
                entity_type="conversation_summaries",
                entity_id=str(contact.id),
                details_json={
                    "contact_id": contact.id,
                    "summary_ids": [row.id for row in due_summaries],
                    "thresholds": [row.threshold for row in due_summaries],
                },
            )
        planned.source_diagnostics.setdefault("memory", {}).update(
            {
                "timeline_event_created": bool(timeline_entry),
                "summaries_created": len(due_summaries),
            }
        )
        await self._save_audit_log(
            action="outbound_queued",
            entity_type="message",
            entity_id=str(outbound.id),
            details_json={
                "inbound_message_id": inbound.id,
                "outbound_queue_id": queued.id,
                "decision_type": planned.decision_type.value,
                "chat_id": normalized.chat_id,
                "media_url": planned.media_url,
                "media_type": planned.media_type,
                "source_diagnostics": planned.source_diagnostics,
            },
        )
        log_event(
            logger,
            logging.INFO,
            "outbound_queued",
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
            outbound_queue_id=queued.id,
            decision_type=planned.decision_type.value,
        )
        await self.session.commit()
        return asdict(RouteResult(
            status="ok",
            chat_type=normalized.chat_type.value,
            action="queued",
            decision_type=planned.decision_type.value,
            reason=planned.reason,
            kb_confidence=planned.kb_confidence,
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
            outbound_queue_id=queued.id,
        ))

    async def preview(self, normalized: NormalizedMessage, contact_id: int | None = None) -> PlannedReply:
        return await self.reply_planner.plan(normalized, contact_id)

    async def close(self) -> None:
        return None

    async def _get_or_create_contact(self, whatsapp_id: str, display_name: str | None) -> Contact:
        stmt = select(Contact).where(Contact.whatsapp_id == whatsapp_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            if display_name and display_name != model.display_name:
                model.display_name = display_name
            model.updated_at = utcnow()
            return model

        model = Contact(whatsapp_id=whatsapp_id or "unknown@local", display_name=display_name, updated_at=utcnow())
        self.session.add(model)
        await self.session.flush()
        return model

    async def _save_inbound_message(self, msg: NormalizedMessage, contact_id: int) -> Message:
        model = Message(
            bot_number_id=None,
            contact_id=contact_id,
            chat_id=msg.chat_id or "unknown-chat",
            chat_type=msg.chat_type.value,
            direction=Direction.INBOUND.value,
            message_text=msg.message_text,
            normalized_text=msg.normalized_text,
            message_type=msg.message_type,
            raw_payload_json=msg.payload,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def _save_outbound_message(
        self,
        msg: NormalizedMessage,
        contact_id: int,
        text: str,
        outbound_queue_id: int,
    ) -> Message:
        model = Message(
            bot_number_id=None,
            contact_id=contact_id,
            chat_id=msg.chat_id or "unknown-chat",
            chat_type=msg.chat_type.value,
            direction=Direction.OUTBOUND.value,
            message_text=text,
            normalized_text=normalize_text(text),
            message_type="text",
            raw_payload_json={"source": "router_queue", "outbound_queue_id": outbound_queue_id},
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def _queue_outbound_message(
        self,
        chat_id: str,
        text: str,
        *,
        media_url: str | None = None,
        media_type: str | None = None,
        media_caption: str | None = None,
    ) -> OutboundMessage:
        model = OutboundMessage(
            chat_id=chat_id or "unknown-chat",
            message_text=text,
            media_url=media_url,
            media_type=media_type,
            media_caption=media_caption,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def _save_router_decision(
        self,
        *,
        message_id: int,
        decision_type: str,
        reason: str,
        confidence: float,
        reply_sent: bool,
    ) -> RouterDecision:
        model = RouterDecision(
            message_id=message_id,
            decision_type=decision_type,
            reason=reason,
            confidence=confidence,
            reply_sent=reply_sent,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def _save_audit_log(
        self,
        *,
        action: str,
        entity_type: str,
        entity_id: str | None,
        details_json: dict[str, Any] | None,
    ) -> AuditLog:
        model = AuditLog(
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details_json=details_json,
        )
        self.session.add(model)
        await self.session.flush()
        return model

    async def _maybe_start_typing(self, chat_id: str) -> bool:
        if not await self.reply_planner.bot_config.get_bool("experience_typing_presence_enabled", False):
            return False
        client = WAHAClient()
        try:
            await client.start_typing(chat_id)
            return True
        except WahaClientError as exc:
            log_event(logger, logging.WARNING, "waha_typing_start_failed", chat_id=chat_id, error=str(exc))
            return False
        finally:
            await client.close()

    async def _maybe_stop_typing(self, chat_id: str) -> None:
        client = WAHAClient()
        try:
            await client.stop_typing(chat_id)
        except WahaClientError as exc:
            log_event(logger, logging.WARNING, "waha_typing_stop_failed", chat_id=chat_id, error=str(exc))
        finally:
            await client.close()

    async def _maybe_typing_delay(self, normalized: NormalizedMessage, planned: PlannedReply) -> None:
        text = normalized.message_text.strip()
        is_command = text.startswith("/") or text.startswith("!")
        enabled = await self.reply_planner.bot_config.get_bool("typing_delay_enabled", settings.typing_delay_enabled)
        min_seconds = await self.reply_planner.bot_config.get_float(
            "min_typing_delay_seconds",
            settings.min_typing_delay_seconds,
        )
        max_seconds = await self.reply_planner.bot_config.get_float(
            "max_typing_delay_seconds",
            settings.max_typing_delay_seconds,
        )
        experience_info = planned.source_diagnostics.setdefault("experience", {})
        reply_mode = "normal"
        if isinstance(experience_info, dict):
            reply_mode = str(experience_info.get("reply_mode") or planned.source_diagnostics.get("reply_mode") or "normal")
        delay = self.reply_planner.formatter.typing_delay_seconds(
            planned.raw_reply_text or planned.reply_text or "",
            enabled=enabled,
            min_seconds=min_seconds,
            max_seconds=max_seconds,
            mode=reply_mode,
            is_command=is_command,
        )
        if isinstance(experience_info, dict):
            experience_info["typing_delay_seconds"] = delay
            experience_info["typing_delay_skipped_for_command"] = is_command and delay == 0
        if delay > 0:
            await asyncio.sleep(delay)

    def _attach_thinking_diagnostics(self, planned: PlannedReply) -> None:
        source = planned.source_diagnostics.get("source")
        if source in {"KB", "FAQ", "Cache"}:
            stage = "knowledge"
        elif source in {"Internet", "Giphy"}:
            stage = "internet"
        elif planned.source_diagnostics.get("memory") or source in {"Memory", "Timeline", "Memory + Timeline"}:
            stage = "memory"
        else:
            stage = "thinking"
        planned.source_diagnostics.setdefault("experience", {})["thinking_indicator"] = (
            self.reply_planner.formatter.thinking_indicator(stage)
        )

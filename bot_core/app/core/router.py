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
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.logging_service import log_event
from app.services.memory_compaction_policy import effective_summary_thresholds
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.outbound_media_metadata_service import OutboundMediaMetadataService
from app.services.owner_command_service import OwnerCommandService
from app.services.router_outbound_authority_service import RouterOutboundAuthorityService
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
    reply_deferred: bool = False


class InboundRouter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.normalizer = MessageNormalizer()
        self.reply_planner = ReplyPlanner(session)

    async def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalizer.normalize(event)
        contact = await self._get_or_create_contact(normalized)
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

        takeover_service = ConversationTakeoverService(self.session)
        wait_for_fabian_first = (
            normalized.chat_type.value == "dm"
            and await takeover_service.should_wait_for_fabian_first(chat_id=normalized.chat_id)
        )

        owner_command = await OwnerCommandService(self.session).handle(normalized, contact)
        owner_chat = self._is_owner_chat_id(normalized.chat_id)
        if owner_command:
            wait_for_fabian_first = False
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

            planned = await self._plan_with_owner_typing(
                normalized,
                contact.id,
                owner_chat=owner_chat,
                wait_for_fabian_first=wait_for_fabian_first,
            )
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
                "question": normalized.message_text,
                "intent": planned.intent,
                "message_id": inbound.id,
                "decision_type": planned.decision_type.value,
                "reason": planned.reason,
                "kb_confidence": planned.kb_confidence,
                "should_reply": planned.should_reply,
                "wait_for_fabian_first": wait_for_fabian_first,
                "source_diagnostics": planned.source_diagnostics,
                "router_analytics": planned.source_diagnostics.get("router_analytics"),
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
            wait_for_fabian_first=wait_for_fabian_first,
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

        requires_owner_approval = owner_command is None and not owner_chat
        reply_deferred = wait_for_fabian_first or requires_owner_approval
        if not reply_deferred:
            await self._maybe_typing_delay(normalized, planned)
        formatting_metadata = self._reply_formatting_metadata(planned)
        formatting_metadata["delivery_policy"] = (
            "approval_required"
            if requires_owner_approval
            else "wait_for_fabian_first"
            if reply_deferred
            else "immediate"
        )
        formatting_metadata["reply_deferred"] = reply_deferred

        # One canonical media contract for every producer that can reach this queue.
        # Normalization happens before the row is created so the authority hash binds a
        # validated locator/kind/caption. Rejected media only drops the attachment; the
        # text reply still goes through the unchanged approval fence.
        canonical_media = None
        if planned.media_url:
            # Named distinctly from the persisted RouterDecision above, which is mutated
            # further down; reusing `decision` here would overwrite that durable row.
            media_decision = OutboundMediaMetadataService.normalize(
                media_url=planned.media_url,
                media_kind=planned.media_type,
                media_caption=planned.media_caption,
                provenance=str(planned.source_diagnostics.get("source") or "reply_planner"),
            )
            if media_decision.accepted:
                canonical_media = media_decision.media
                formatting_metadata.update(canonical_media.queue_metadata())
            else:
                planned.source_diagnostics.setdefault("outbound_media", {}).update(
                    {"accepted": False, "reason": media_decision.reason}
                )
                log_event(
                    logger,
                    logging.WARNING,
                    "outbound_media_rejected",
                    chat_id=normalized.chat_id,
                    reason=media_decision.reason,
                )

        queued = await self._queue_outbound_message(
            normalized.chat_id,
            planned.reply_text,
            media_url=canonical_media.media_url if canonical_media else None,
            media_type=canonical_media.media_kind if canonical_media else None,
            media_caption=canonical_media.media_caption if canonical_media else None,
            formatting_json=formatting_metadata,
            delivery_status="deferred" if reply_deferred else "pending",
        )
        approval_id: int | None = None
        if requires_owner_approval:
            prepared = await RouterOutboundAuthorityService(self.session).prepare_external_reply(
                queued,
                inbound_message_id=inbound.id,
                contact_id=contact.id,
                response_category="normal_reply",
            )
            approval_id = prepared.approval_id
            formatting_metadata = dict(queued.formatting_json or {})
            planned.source_diagnostics.setdefault("outbound_authority", {}).update(
                {
                    "approval_required": True,
                    "approval_id": approval_id,
                    "response_category": prepared.context.response_category,
                }
            )
        outbound = await self._save_outbound_message(
            normalized,
            contact.id,
            planned.reply_text,
            queued.id,
            raw_reply_text=planned.raw_reply_text,
            formatting_json=formatting_metadata,
        )
        decision.reply_sent = not reply_deferred
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
        if not reply_deferred:
            await self.reply_planner.upsert_conversation_summary(
                chat_id=normalized.chat_id,
                chat_type=normalized.chat_type.value,
                user_text=normalized.message_text,
                bot_text=planned.raw_reply_text or planned.reply_text,
                decision=planned.decision_type.value,
            )
        timeline_entry = await self.reply_planner.memory_service.log_conversation_event(
            contact.id,
            user_text=normalized.message_text,
            decision=planned.decision_type.value,
        )
        threshold_config = await self.reply_planner.bot_config.get("memory_summary_thresholds", "25,50,100")
        configured_thresholds = self.reply_planner.memory_service.parse_summary_thresholds(threshold_config)
        summary_thresholds = await effective_summary_thresholds(
            self.session,
            contact.id,
            configured_thresholds,
        )
        due_summaries = await self.reply_planner.memory_service.generate_due_summaries(
            contact.id,
            chat_id=normalized.chat_id,
            thresholds=summary_thresholds,
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
                    "configured_thresholds": list(configured_thresholds),
                    "effective_thresholds": list(summary_thresholds),
                },
            )
        planned.source_diagnostics.setdefault("memory", {}).update(
            {
                "timeline_event_created": bool(timeline_entry),
                "summaries_created": len(due_summaries),
                "summary_thresholds": list(summary_thresholds),
                "assistant_reply_deferred": reply_deferred,
            }
        )
        audit_action = "outbound_deferred" if reply_deferred else "outbound_queued"
        await self._save_audit_log(
            action=audit_action,
            entity_type="message",
            entity_id=str(outbound.id),
            details_json={
                "inbound_message_id": inbound.id,
                "outbound_queue_id": queued.id,
                "approval_id": approval_id,
                "decision_type": planned.decision_type.value,
                "chat_id": normalized.chat_id,
                "media_url": planned.media_url,
                "media_type": planned.media_type,
                "raw_reply_text": planned.raw_reply_text,
                "final_reply_text": planned.reply_text,
                "formatting": formatting_metadata,
                "source_diagnostics": planned.source_diagnostics,
                "reply_deferred": reply_deferred,
            },
        )
        log_event(
            logger,
            logging.INFO,
            audit_action,
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
            outbound_queue_id=queued.id,
            approval_id=approval_id,
            decision_type=planned.decision_type.value,
            reply_deferred=reply_deferred,
        )
        await self.session.commit()
        return asdict(RouteResult(
            status="ok",
            chat_type=normalized.chat_type.value,
            action="deferred" if reply_deferred else "queued",
            decision_type=planned.decision_type.value,
            reason=planned.reason,
            kb_confidence=planned.kb_confidence,
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
            outbound_queue_id=queued.id,
            reply_deferred=reply_deferred,
        ))

    async def preview(self, normalized: NormalizedMessage, contact_id: int | None = None) -> PlannedReply:
        return await self.reply_planner.plan(normalized, contact_id)

    async def close(self) -> None:
        return None

    @staticmethod
    def _is_owner_chat_id(chat_id: str) -> bool:
        wanted = (chat_id or "").strip().lower()
        if not wanted:
            return False
        owner_ids = {
            item.strip().lower()
            for item in str(settings.owner_whatsapp_ids or "").replace(";", ",").split(",")
            if item.strip()
        }
        return wanted in owner_ids

    async def _plan_with_owner_typing(
        self,
        normalized: NormalizedMessage,
        contact_id: int,
        *,
        owner_chat: bool,
        wait_for_fabian_first: bool,
    ) -> PlannedReply:
        typing_started = False
        planner_error: BaseException | None = None
        try:
            if owner_chat and not wait_for_fabian_first:
                typing_started = await self._maybe_start_typing(normalized.chat_id)
            return await self.reply_planner.plan(normalized, contact_id)
        except BaseException as exc:
            planner_error = exc
            raise
        finally:
            if typing_started:
                try:
                    await self._maybe_stop_typing(normalized.chat_id)
                except BaseException as cleanup_exc:
                    if planner_error is None:
                        raise
                    log_event(
                        logger,
                        logging.WARNING,
                        "waha_typing_cleanup_failed",
                        chat_id=normalized.chat_id,
                        error=str(cleanup_exc),
                    )

    async def _get_or_create_contact(self, normalized: NormalizedMessage) -> Contact:
        whatsapp_id = normalized.sender_id
        identity = normalized.sender_identity or {}
        display_name = self._resolved_display_name(identity, normalized.sender_name)
        stmt = select(Contact).where(Contact.whatsapp_id == whatsapp_id).limit(1).with_for_update()
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            if display_name and display_name != model.display_name and not getattr(model, "is_name_verified", False):
                model.display_name = display_name
            self._apply_contact_identity(model, normalized, identity)
            model.updated_at = utcnow()
            return model

        model = Contact(whatsapp_id=whatsapp_id or "unknown@local", display_name=display_name, updated_at=utcnow())
        self._apply_contact_identity(model, normalized, identity)
        self.session.add(model)
        await self.session.flush()
        return model

    @staticmethod
    def _resolved_display_name(identity: dict[str, Any], fallback: str | None) -> str | None:
        for key in ("contact_name", "push_name", "profile_name", "display_name", "normalized_phone"):
            value = identity.get(key) if isinstance(identity, dict) else None
            text = " ".join(str(value or "").strip().split())
            if text:
                return text[:180]
        return fallback

    @staticmethod
    def _apply_contact_identity(model: Contact, normalized: NormalizedMessage, identity: dict[str, Any]) -> None:
        model.chat_id = normalized.chat_id
        model.whatsapp_phone = identity.get("phone") or model.whatsapp_phone
        model.normalized_phone = identity.get("normalized_phone") or model.normalized_phone
        model.waha_contact_id = identity.get("waha_contact_id") or model.waha_contact_id
        model.waha_participant_id = identity.get("waha_participant_id") or model.waha_participant_id
        model.push_name = identity.get("push_name") or model.push_name
        model.contact_name = identity.get("contact_name") or model.contact_name
        model.profile_image_url = identity.get("profile_image_url") or model.profile_image_url
        model.identity_source = (
            "contact_name"
            if identity.get("contact_name")
            else "push_name"
            if identity.get("push_name")
            else "phone"
            if identity.get("normalized_phone")
            else model.identity_source
        )
        previous_identity = dict(model.identity_json) if isinstance(model.identity_json, dict) else {}
        merged_identity = dict(identity) if isinstance(identity, dict) else {}
        for key in (
            "is_saved_contact",
            "saved_contact_synced_at",
            "saved_contact_reconciled_reason",
        ):
            if key not in merged_identity and key in previous_identity:
                merged_identity[key] = previous_identity[key]
        model.identity_json = merged_identity or model.identity_json
        model.last_active_at = utcnow()

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
        *,
        raw_reply_text: str | None = None,
        formatting_json: dict[str, Any] | None = None,
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
            raw_payload_json={
                "source": "router_queue",
                "outbound_queue_id": outbound_queue_id,
                "raw_reply_text": raw_reply_text or text,
                "final_reply_text": text,
                "formatting": formatting_json or {},
            },
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
        formatting_json: dict[str, Any] | None = None,
        delivery_status: str = "pending",
    ) -> OutboundMessage:
        model = OutboundMessage(
            chat_id=chat_id or "unknown-chat",
            message_text=text,
            media_url=media_url,
            media_type=media_type,
            media_caption=media_caption,
            formatting_json=formatting_json,
            status=delivery_status,
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            updated_at=utcnow(),
        )
        self.session.add(model)
        await self.session.flush()
        # Owner-destined rows are authorized by exact destination at the delivery fence,
        # which does not by itself bind the payload. Stamp the canonical payload binding
        # after flush so the final stored content is what is committed to.
        if self._is_owner_chat_id(model.chat_id):
            model.formatting_json = OutboundAuthorizationService.stamp_owner_payload(model)
            await self.session.flush()
        return model

    @staticmethod
    def _reply_formatting_metadata(planned: PlannedReply) -> dict[str, Any]:
        experience = planned.source_diagnostics.get("experience")
        if not isinstance(experience, dict):
            experience = {}
        return {
            "raw_reply_text": planned.raw_reply_text or planned.reply_text,
            "final_reply_text": planned.reply_text,
            "whatsapp_message_format": experience.get("whatsapp_message_format", "standard"),
            "quote_rendered": bool(experience.get("quote_rendered")),
            "quote_applied": bool(experience.get("quote_applied")),
            "quote_reason": experience.get("quote_reason"),
        }

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
        elif planned.ai_used or source in {"AI", "Global Chat"}:
            stage = "thinking"
        else:
            return
        planned.source_diagnostics.setdefault("experience", {})["thinking_indicator"] = (
            self.reply_planner.formatter.thinking_indicator(stage)
        )

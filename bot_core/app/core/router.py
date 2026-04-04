from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.message_normalizer import MessageNormalizer, NormalizedMessage
from app.core.reply_planner import PlannedReply, ReplyPlanner
from app.models.enums import Direction
from app.models.schema import AuditLog, Contact, Message, RouterDecision
from app.services.logging_service import log_event
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.text import normalize_text


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
    delivery_error: str | None = None


class InboundRouter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.normalizer = MessageNormalizer()
        self.reply_planner = ReplyPlanner(session)
        self.waha = WAHAClient()

    async def process_event(self, event: dict[str, Any]) -> dict[str, Any]:
        normalized = self.normalizer.normalize(event)
        contact = await self._get_or_create_contact(normalized.sender_id, normalized.sender_name)
        inbound = await self._save_inbound_message(normalized, contact.id)
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

        planned = await self.reply_planner.plan(normalized, contact.id)
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
        await self.session.commit()

        if not planned.should_reply or not planned.reply_text:
            return RouteResult(
                status="ok",
                chat_type=normalized.chat_type.value,
                action="ignored",
                decision_type=planned.decision_type.value,
                reason=planned.reason,
                kb_confidence=planned.kb_confidence,
                inbound_message_id=inbound.id,
                outbound_message_id=None,
            ).__dict__

        try:
            waha_response = await self.waha.send_text(chat_id=normalized.chat_id, text=planned.reply_text)
        except WahaClientError as exc:
            await self._save_audit_log(
                action="outbound_failed",
                entity_type="message",
                entity_id=str(inbound.id),
                details_json={"decision_type": planned.decision_type.value, "error": str(exc)},
            )
            log_event(logger, logging.ERROR, "outbound_failed", message_id=inbound.id, error=str(exc))
            await self.session.commit()
            return RouteResult(
                status="delivery_failed",
                chat_type=normalized.chat_type.value,
                action="delivery_failed",
                decision_type=planned.decision_type.value,
                reason=planned.reason,
                kb_confidence=planned.kb_confidence,
                inbound_message_id=inbound.id,
                outbound_message_id=None,
                delivery_error=str(exc),
            ).__dict__

        outbound = await self._save_outbound_message(normalized, contact.id, planned.reply_text, waha_response)
        decision.reply_sent = True
        if planned.ai_call:
            planned.ai_call.message_id = inbound.id
            self.session.add(planned.ai_call)
        await self.reply_planner.cache_answer_if_reusable(normalized.message_text, planned)
        await self.reply_planner.upsert_conversation_summary(
            chat_id=normalized.chat_id,
            chat_type=normalized.chat_type.value,
            user_text=normalized.message_text,
            bot_text=planned.reply_text,
            decision=planned.decision_type.value,
        )
        await self._save_audit_log(
            action="outbound_sent",
            entity_type="message",
            entity_id=str(outbound.id),
            details_json={
                "inbound_message_id": inbound.id,
                "decision_type": planned.decision_type.value,
                "chat_id": normalized.chat_id,
            },
        )
        log_event(
            logger,
            logging.INFO,
            "outbound_sent",
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
            decision_type=planned.decision_type.value,
        )
        await self.session.commit()
        return RouteResult(
            status="ok",
            chat_type=normalized.chat_type.value,
            action="replied",
            decision_type=planned.decision_type.value,
            reason=planned.reason,
            kb_confidence=planned.kb_confidence,
            inbound_message_id=inbound.id,
            outbound_message_id=outbound.id,
        ).__dict__

    async def preview(self, normalized: NormalizedMessage, contact_id: int | None = None) -> PlannedReply:
        return await self.reply_planner.plan(normalized, contact_id)

    async def close(self) -> None:
        await self.waha.close()

    async def _get_or_create_contact(self, whatsapp_id: str, display_name: str | None) -> Contact:
        stmt = select(Contact).where(Contact.whatsapp_id == whatsapp_id).limit(1)
        model = (await self.session.execute(stmt)).scalar_one_or_none()
        if model:
            if display_name and display_name != model.display_name:
                model.display_name = display_name
            return model

        model = Contact(whatsapp_id=whatsapp_id or "unknown@local", display_name=display_name)
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
        waha_response: dict[str, Any],
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
            raw_payload_json={"source": "router", "waha_response": waha_response},
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

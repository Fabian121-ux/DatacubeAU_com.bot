from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, Message, OutboundMessage
from app.utils.time import utcnow


class ConversationHandbackService:
    """Build and persist Fabian-only summaries when he resumes a Zina-assisted DM."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def generate_if_needed(self, *, chat_id: str) -> dict[str, Any] | None:
        row = await self._get_locked(chat_id)
        if row is None or row.state != "fabian_resumed" or row.assisting_since is None:
            return None

        metadata = dict(row.metadata_json or {})
        existing = metadata.get("handback_summary")
        assisting_key = row.assisting_since.isoformat()
        if isinstance(existing, dict) and existing.get("for_assisting_since") == assisting_key:
            return existing

        now = utcnow()
        window_start = await self._resolve_window_start(chat_id=chat_id, assisting_since=row.assisting_since)
        messages = (
            await self.session.execute(
                select(Message)
                .where(Message.chat_id == chat_id)
                .where(Message.created_at >= window_start)
                .where(Message.created_at <= now)
                .order_by(Message.created_at, Message.id)
            )
        ).scalars().all()
        outbound = (
            await self.session.execute(
                select(OutboundMessage)
                .where(OutboundMessage.chat_id == chat_id)
                .where(OutboundMessage.updated_at >= row.assisting_since)
                .where(OutboundMessage.updated_at <= now)
                .order_by(OutboundMessage.updated_at, OutboundMessage.id)
            )
        ).scalars().all()

        inbound_messages = [item for item in messages if item.direction == "inbound"]
        latest_inbound = self._clip(inbound_messages[-1].message_text) if inbound_messages else None
        recent_questions = [
            self._clip(item.message_text)
            for item in inbound_messages
            if "?" in (item.message_text or "")
        ][-3:]

        sent_statuses = {"sent", "delivered"}
        pending_statuses = {"pending", "retrying", "sending", "deferred"}
        failed_statuses = {"failed", "cancelled"}
        sent_count = sum(1 for item in outbound if item.status in sent_statuses)
        pending_count = sum(1 for item in outbound if item.status in pending_statuses)
        failed_count = sum(1 for item in outbound if item.status in failed_statuses)

        summary_text = self._build_summary_text(
            inbound_count=len(inbound_messages),
            sent_count=sent_count,
            pending_count=pending_count,
            failed_count=failed_count,
            latest_inbound=latest_inbound,
            recent_questions=recent_questions,
        )
        summary: dict[str, Any] = {
            "for_assisting_since": assisting_key,
            "generated_at": now.isoformat(),
            "window_start": window_start.isoformat(),
            "window_end": now.isoformat(),
            "summary_text": summary_text,
            "contact_messages": len(inbound_messages),
            "zina_messages_sent": sent_count,
            "zina_messages_pending": pending_count,
            "zina_messages_failed_or_cancelled": failed_count,
            "latest_contact_message": latest_inbound,
            "recent_questions_to_review": recent_questions,
        }
        metadata["handback_summary"] = summary
        row.metadata_json = metadata
        row.updated_at = now
        self.session.add(
            AuditLog(
                action="conversation_handback_summary_generated",
                entity_type="conversation_takeover",
                entity_id=chat_id,
                details_json={
                    "chat_id": chat_id,
                    "for_assisting_since": assisting_key,
                    "contact_messages": len(inbound_messages),
                    "zina_messages_sent": sent_count,
                    "zina_messages_pending": pending_count,
                    "zina_messages_failed_or_cancelled": failed_count,
                    "recent_questions_to_review": recent_questions,
                },
            )
        )
        await self.session.flush()
        return summary

    async def get_latest(self, *, chat_id: str) -> dict[str, Any] | None:
        row = await self._get(chat_id)
        if row is None:
            return None
        summary = (row.metadata_json or {}).get("handback_summary")
        return summary if isinstance(summary, dict) else None

    async def _resolve_window_start(self, *, chat_id: str, assisting_since):
        """Recover the human-first waiting window even after owner-resume clears pending_since."""
        stmt = (
            select(AuditLog)
            .where(AuditLog.action == "conversation_takeover_waiting")
            .where(AuditLog.entity_type == "conversation_takeover")
            .where(AuditLog.entity_id == chat_id)
            .where(AuditLog.created_at <= assisting_since)
            .order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
            .limit(1)
        )
        waiting_event = (await self.session.execute(stmt)).scalar_one_or_none()
        return waiting_event.created_at if waiting_event is not None else assisting_since

    async def _get(self, chat_id: str) -> ConversationTakeover | None:
        stmt = select(ConversationTakeover).where(ConversationTakeover.chat_id == chat_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_locked(self, chat_id: str) -> ConversationTakeover | None:
        stmt = (
            select(ConversationTakeover)
            .where(ConversationTakeover.chat_id == chat_id)
            .limit(1)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    @staticmethod
    def _clip(value: str | None, *, limit: int = 220) -> str:
        text = " ".join((value or "").split())
        if len(text) <= limit:
            return text
        return text[: limit - 1].rstrip() + "…"

    @staticmethod
    def _build_summary_text(
        *,
        inbound_count: int,
        sent_count: int,
        pending_count: int,
        failed_count: int,
        latest_inbound: str | None,
        recent_questions: list[str],
    ) -> str:
        parts = [
            f"Zina handback: {inbound_count} contact message(s) arrived while you were away.",
            f"Zina sent {sent_count} WhatsApp message(s); {pending_count} remain pending and {failed_count} failed or were cancelled.",
        ]
        if latest_inbound:
            parts.append(f'Latest contact message: “{latest_inbound}”.')
        if recent_questions:
            rendered = " | ".join(f'“{question}”' for question in recent_questions)
            parts.append(f"Questions to review: {rendered}.")
        return " ".join(parts)

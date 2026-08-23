from __future__ import annotations

import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, Message, OutboundMessage
from app.utils.time import utcnow


class ConversationHandbackService:
    """Build and persist Fabian-only summaries when he resumes a Zina-assisted DM."""

    _request_pattern = re.compile(
        r"\b(?:can|could|would|will)\s+(?:fabian|he|you)\b|"
        r"\b(?:please|need|want|confirm|send|call|share|check|review|let\s+(?:fabian|him)\s+know)\b",
        re.IGNORECASE,
    )
    _attention_pattern = re.compile(
        r"\b(?:urgent|asap|deadline|today|tomorrow|tonight|by\s+\w+|before\s+\w+|confirm|decision|approve)\b",
        re.IGNORECASE,
    )
    _time_pattern = re.compile(
        r"\b(?:today|tomorrow|tonight|this\s+morning|this\s+afternoon|this\s+evening|"
        r"monday|tuesday|wednesday|thursday|friday|saturday|sunday|"
        r"\d{1,2}(?::\d{2})?\s?(?:am|pm)|"
        r"\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)\b",
        re.IGNORECASE,
    )
    _commitment_pattern = re.compile(
        r"\b(?:i['’]?ll|i\s+will|we['’]?ll|we\s+will|fabian\s+will|"
        r"i['’]?ll\s+(?:ask|tell|let|send|check|confirm)|i\s+can|we\s+can)\b",
        re.IGNORECASE,
    )

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

        contact_requests = self._extract_contact_requests(inbound_messages)
        zina_responses = self._extract_zina_responses(outbound, sent_statuses=sent_statuses)
        time_references = self._extract_time_references(inbound_messages, outbound)
        commitment_evidence = self._extract_commitment_evidence(outbound, sent_statuses=sent_statuses)
        attention_items = self._build_attention_items(
            inbound_messages=inbound_messages,
            recent_questions=recent_questions,
            pending_count=pending_count,
            failed_count=failed_count,
        )

        summary_text = self._build_summary_text(
            inbound_count=len(inbound_messages),
            sent_count=sent_count,
            pending_count=pending_count,
            failed_count=failed_count,
            latest_inbound=latest_inbound,
            recent_questions=recent_questions,
            contact_requests=contact_requests,
            attention_items=attention_items,
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
            "contact_requests": contact_requests,
            "zina_responses_sent": zina_responses,
            "explicit_time_references": time_references,
            "zina_commitment_evidence": commitment_evidence,
            "needs_fabian_attention": attention_items,
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
                    "contact_requests": contact_requests,
                    "needs_fabian_attention": attention_items,
                    "time_reference_count": len(time_references),
                    "commitment_evidence_count": len(commitment_evidence),
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

    @classmethod
    def _extract_contact_requests(cls, messages: list[Message]) -> list[str]:
        requests = []
        for item in messages:
            text = cls._clip(item.message_text)
            if text and ("?" in text or cls._request_pattern.search(text)):
                requests.append(text)
        return cls._dedupe(requests)[-4:]

    @classmethod
    def _extract_zina_responses(
        cls,
        outbound: list[OutboundMessage],
        *,
        sent_statuses: set[str],
    ) -> list[str]:
        responses = []
        for item in outbound:
            if item.status not in sent_statuses:
                continue
            formatting = item.formatting_json or {}
            if formatting.get("source") == "conversation_takeover":
                continue
            text = cls._clip(item.message_text)
            if text:
                responses.append(text)
        return cls._dedupe(responses)[-4:]

    @classmethod
    def _extract_time_references(
        cls,
        inbound_messages: list[Message],
        outbound: list[OutboundMessage],
    ) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for item in inbound_messages:
            text = cls._clip(item.message_text)
            refs = cls._time_pattern.findall(text)
            if refs:
                evidence.append({"source": "contact", "message": text, "references": cls._dedupe(refs)})
        for item in outbound:
            text = cls._clip(item.message_text)
            refs = cls._time_pattern.findall(text)
            if refs:
                evidence.append(
                    {
                        "source": "zina",
                        "message": text,
                        "delivery_status": item.status,
                        "references": cls._dedupe(refs),
                    }
                )
        return evidence[-6:]

    @classmethod
    def _extract_commitment_evidence(
        cls,
        outbound: list[OutboundMessage],
        *,
        sent_statuses: set[str],
    ) -> list[dict[str, str]]:
        evidence: list[dict[str, str]] = []
        for item in outbound:
            if item.status not in sent_statuses:
                continue
            text = cls._clip(item.message_text)
            if text and cls._commitment_pattern.search(text):
                evidence.append({"message": text, "delivery_status": item.status})
        return evidence[-4:]

    @classmethod
    def _build_attention_items(
        cls,
        *,
        inbound_messages: list[Message],
        recent_questions: list[str],
        pending_count: int,
        failed_count: int,
    ) -> list[str]:
        items = list(recent_questions)
        for message in inbound_messages:
            text = cls._clip(message.message_text)
            if text and cls._attention_pattern.search(text):
                items.append(text)
        if pending_count:
            items.append(f"{pending_count} Zina message(s) are still pending delivery.")
        if failed_count:
            items.append(f"{failed_count} Zina message(s) failed or were cancelled.")
        return cls._dedupe(items)[-6:]

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
    def _dedupe(values: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for value in values:
            normalized = value.strip().lower()
            if normalized and normalized not in seen:
                seen.add(normalized)
                result.append(value)
        return result

    @staticmethod
    def _build_summary_text(
        *,
        inbound_count: int,
        sent_count: int,
        pending_count: int,
        failed_count: int,
        latest_inbound: str | None,
        recent_questions: list[str],
        contact_requests: list[str],
        attention_items: list[str],
    ) -> str:
        parts = [
            f"Zina handback: {inbound_count} contact message(s) arrived while you were away.",
            f"Zina sent {sent_count} WhatsApp message(s); {pending_count} remain pending and {failed_count} failed or were cancelled.",
        ]
        if contact_requests:
            rendered_requests = " | ".join(f'“{request}”' for request in contact_requests[-2:])
            parts.append(f"What the contact wanted: {rendered_requests}.")
        if latest_inbound:
            parts.append(f'Latest contact message: “{latest_inbound}”.')
        if recent_questions:
            rendered = " | ".join(f'“{question}”' for question in recent_questions)
            parts.append(f"Questions to review: {rendered}.")
        if attention_items:
            parts.append(f"Fabian attention items: {len(attention_items)}.")
        return " ".join(parts)

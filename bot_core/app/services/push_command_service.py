from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AdminAccount, AuditLog, Contact, Message, OutboundMessage
from app.services.admin_management_service import AdminManagementService
from app.utils.time import utcnow


@dataclass(slots=True)
class PushCommandResult:
    consumed: bool
    outbound_queue_id: int | None = None
    error: str | None = None


class PushCommandService:
    """Push a quoted WhatsApp message into Fabian's private self-DM control inbox.

    This service is intentionally narrow: it resolves the quoted source by WAHA message
    ID from Zina's existing PostgreSQL message history, creates a safe text projection,
    and hands delivery to the existing outbound queue. It does not create a parallel
    message store, forward raw WAHA payloads, or persist private notes as Memory.
    """

    COMMAND = "/push"

    def __init__(self, session: AsyncSession):
        self.session = session

    async def handle(
        self,
        message: Any,
        *,
        owner: AdminAccount,
        args: str = "",
        transport_message_id: str | None = None,
        request_id: str | None = None,
    ) -> PushCommandResult:
        owner_chat_id = self._owner_chat_id(owner)
        if not owner_chat_id:
            return PushCommandResult(consumed=True, error="owner self-DM identity unavailable")

        quoted_id = self._quoted_message_id(getattr(message, "payload", None))
        if not quoted_id:
            return await self._queue_private_error(
                owner_chat_id,
                "Reply to the WhatsApp message you want to push, then send .push.",
                transport_message_id=transport_message_id,
            )

        existing = await self._existing_push(transport_message_id)
        if existing is not None:
            return PushCommandResult(consumed=True, outbound_queue_id=existing.id)

        source = await self._source_message(chat_id=str(message.chat_id), quoted_id=quoted_id)
        if source is None:
            return await self._queue_private_error(
                owner_chat_id,
                "I can see the quoted WhatsApp message ID, but that source message is not in Zina's captured history.",
                transport_message_id=transport_message_id,
            )

        source_contact = None
        if source.contact_id is not None:
            source_contact = await self.session.get(Contact, source.contact_id)

        note = self._private_note(args)
        projection = self._render_projection(source, source_contact, quoted_id=quoted_id, note=note)
        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=projection,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={
                "source": "owner_push",
                "command": self.COMMAND,
                "command_message_id": transport_message_id,
                "source_message_id": quoted_id,
                "source_chat_id": source.chat_id,
                "source_db_message_id": source.id,
            },
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()

        self.session.add(
            AuditLog(
                action="message_pushed_to_owner",
                entity_type="message",
                entity_id=str(source.id),
                details_json={
                    "request_id": request_id,
                    "transport_message_id": transport_message_id,
                    "source_message_id": quoted_id,
                    "source_chat_id": source.chat_id,
                    "source_message_type": source.message_type,
                    "outbound_queue_id": queued.id,
                    "note_attached": bool(note),
                },
            )
        )
        await self.session.flush()
        return PushCommandResult(consumed=True, outbound_queue_id=queued.id)

    async def _source_message(self, *, chat_id: str, quoted_id: str) -> Message | None:
        payload = Message.raw_payload_json
        stmt = (
            select(Message)
            .where(
                Message.chat_id == chat_id,
                or_(
                    payload["id"].as_string() == quoted_id,
                    payload["message"]["id"].as_string() == quoted_id,
                ),
            )
            .order_by(Message.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _existing_push(self, transport_message_id: str | None) -> OutboundMessage | None:
        if not transport_message_id:
            return None
        metadata = OutboundMessage.formatting_json
        stmt = (
            select(OutboundMessage)
            .where(
                metadata["source"].as_string() == "owner_push",
                metadata["command_message_id"].as_string() == transport_message_id,
            )
            .order_by(OutboundMessage.id.desc())
            .limit(1)
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _queue_private_error(
        self,
        owner_chat_id: str,
        text: str,
        *,
        transport_message_id: str | None,
    ) -> PushCommandResult:
        queued = OutboundMessage(
            chat_id=owner_chat_id,
            message_text=text,
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow(),
            formatting_json={
                "source": "owner_push",
                "command": self.COMMAND,
                "command_message_id": transport_message_id,
                "error": True,
            },
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()
        return PushCommandResult(consumed=True, outbound_queue_id=queued.id, error=text)

    @staticmethod
    def _quoted_message_id(payload: Any) -> str | None:
        if not isinstance(payload, dict):
            return None
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return None
        raw_id = reply_to.get("id")
        text = str(raw_id or "").strip()
        return text or None

    @staticmethod
    def _owner_chat_id(owner: AdminAccount) -> str | None:
        for raw in (owner.normalized_whatsapp_id, owner.whatsapp_number):
            normalized = AdminManagementService.normalize_whatsapp_id(raw)
            if normalized:
                return normalized
        return None

    @staticmethod
    def _private_note(args: str) -> str | None:
        text = (args or "").strip()
        if not text:
            return None
        if text.lower().startswith("note "):
            text = text[5:].strip()
        return text[:1000] or None

    @staticmethod
    def _render_projection(
        source: Message,
        source_contact: Contact | None,
        *,
        quoted_id: str,
        note: str | None,
    ) -> str:
        if source.direction == "outbound":
            sender = "Fabian"
        else:
            sender = (
                (source_contact.display_name if source_contact else None)
                or (source_contact.contact_name if source_contact else None)
                or (source_contact.push_name if source_contact else None)
                or (source_contact.whatsapp_id if source_contact else None)
                or "Unknown contact"
            )
        body = (source.message_text or "").strip() or "(no text/caption captured)"
        parts = [
            "📌 Pushed message",
            "",
            f"From: {sender}",
            f"Chat: {source.chat_id}",
            f"Sent: {source.created_at.isoformat() if source.created_at else 'unknown'}",
            f"Type: {source.message_type or 'unknown'}",
            f"Source ID: {quoted_id}",
            "",
            body,
        ]
        if (source.message_type or "text").lower() != "text":
            parts.extend(["", "Media: original media is not forwarded by .push in this version; captured text/caption and metadata are preserved."])
        if note:
            parts.extend(["", f"Private note: {note}"])
        return "\n".join(parts)

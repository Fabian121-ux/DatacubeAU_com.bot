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


@dataclass(slots=True)
class PushSource:
    source_message_id: str
    chat_id: str
    db_message_id: int | None
    contact_id: int | None
    direction: str | None
    message_text: str
    message_type: str
    created_at: Any | None
    evidence_source: str


class PushCommandService:
    """Push a quoted WhatsApp message into Fabian's private self-DM control inbox.

    Zina prefers its existing PostgreSQL Message evidence. For owner-authored or other
    quoted messages that were never stored in Message history, WAHA's authenticated
    `replyTo` snapshot is used as bounded transport evidence and the resulting source
    ID/text metadata is persisted on the owner-only outbound queue record. This avoids
    pretending that an unavailable historical source exists while still supporting a
    quoted owner message whose transport ID is present only in the current WAHA event.

    Private notes are intentionally not accepted from a peer DM: anything Fabian types
    there is visible to that peer before Zina receives the webhook. A later private
    self-DM annotation flow can add notes without making a false privacy promise.
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

        # Do not describe peer-visible command arguments as private. `.push` must be
        # sent alone while replying to the source message.
        if (args or "").strip():
            return await self._queue_private_error(
                owner_chat_id,
                "Send .push by itself while replying to the source message. Private notes are not accepted from a peer chat because that text is visible to the peer.",
                transport_message_id=transport_message_id,
            )

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

        source_message = await self._source_message(chat_id=str(message.chat_id), quoted_id=quoted_id)
        source = self._message_source(source_message, quoted_id=quoted_id) if source_message else None
        if source is None:
            source = self._reply_snapshot_source(message, quoted_id=quoted_id)
        if source is None:
            return await self._queue_private_error(
                owner_chat_id,
                "I can see the quoted WhatsApp message ID, but Zina has neither captured history nor a usable WAHA reply snapshot for that source.",
                transport_message_id=transport_message_id,
            )

        source_contact = None
        if source.contact_id is not None:
            source_contact = await self.session.get(Contact, source.contact_id)
        if source_contact is None:
            source_contact = await self._contact_for_chat(source.chat_id)

        projection = self._render_projection(source, source_contact)
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
                "source_message_id": source.source_message_id,
                "source_chat_id": source.chat_id,
                "source_db_message_id": source.db_message_id,
                "source_evidence": source.evidence_source,
                "source_message_type": source.message_type,
            },
            updated_at=utcnow(),
        )
        self.session.add(queued)
        await self.session.flush()

        self.session.add(
            AuditLog(
                action="message_pushed_to_owner",
                entity_type="message",
                entity_id=str(source.db_message_id or source.source_message_id),
                details_json={
                    "request_id": request_id,
                    "transport_message_id": transport_message_id,
                    "source_message_id": source.source_message_id,
                    "source_chat_id": source.chat_id,
                    "source_message_type": source.message_type,
                    "source_evidence": source.evidence_source,
                    "outbound_queue_id": queued.id,
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

    async def _contact_for_chat(self, chat_id: str) -> Contact | None:
        stmt = (
            select(Contact)
            .where(or_(Contact.chat_id == chat_id, Contact.whatsapp_id == chat_id))
            .order_by(Contact.id.desc())
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
        existing = await self._existing_push(transport_message_id)
        if existing is not None:
            return PushCommandResult(consumed=True, outbound_queue_id=existing.id, error=text)
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
    def _message_source(source: Message, *, quoted_id: str) -> PushSource:
        return PushSource(
            source_message_id=quoted_id,
            chat_id=source.chat_id,
            db_message_id=source.id,
            contact_id=source.contact_id,
            direction=source.direction,
            message_text=source.message_text,
            message_type=source.message_type or "text",
            created_at=source.created_at,
            evidence_source="postgres_message",
        )

    @staticmethod
    def _reply_snapshot_source(message: Any, *, quoted_id: str) -> PushSource | None:
        payload = getattr(message, "payload", None)
        if not isinstance(payload, dict):
            return None
        reply_to = payload.get("replyTo")
        if not isinstance(reply_to, dict):
            return None
        body = str(reply_to.get("body") or reply_to.get("caption") or "").strip()
        if not body:
            return None
        from_me = reply_to.get("fromMe")
        direction = "outbound" if from_me is True else "inbound" if from_me is False else None
        message_type = str(reply_to.get("type") or reply_to.get("messageType") or "text").strip() or "text"
        return PushSource(
            source_message_id=quoted_id,
            chat_id=str(getattr(message, "chat_id", "") or payload.get("chatId") or ""),
            db_message_id=None,
            contact_id=None,
            direction=direction,
            message_text=body,
            message_type=message_type,
            created_at=None,
            evidence_source="waha_reply_snapshot",
        )

    @staticmethod
    def _owner_chat_id(owner: AdminAccount) -> str | None:
        for raw in (owner.normalized_whatsapp_id, owner.whatsapp_number):
            normalized = AdminManagementService.normalize_whatsapp_id(raw)
            if normalized:
                return normalized
        return None

    @staticmethod
    def _render_projection(source: PushSource, source_contact: Contact | None) -> str:
        if source.direction == "outbound":
            sender = "Fabian"
        elif source.direction == "inbound":
            sender = (
                (source_contact.display_name if source_contact else None)
                or (source_contact.contact_name if source_contact else None)
                or (source_contact.push_name if source_contact else None)
                or (source_contact.whatsapp_id if source_contact else None)
                or "Unknown contact"
            )
        else:
            sender = "Quoted WhatsApp message (sender not present in reply snapshot)"
        body = (source.message_text or "").strip() or "(no text/caption captured)"
        parts = [
            "📌 Pushed message",
            "",
            f"From: {sender}",
            f"Chat: {source.chat_id}",
            f"Sent: {source.created_at.isoformat() if source.created_at else 'timestamp unavailable in reply snapshot'}",
            f"Type: {source.message_type or 'unknown'}",
            f"Source ID: {source.source_message_id}",
            f"Evidence: {source.evidence_source}",
            "",
            body,
        ]
        if (source.message_type or "text").lower() != "text":
            parts.extend(["", "Media: original media is not forwarded by .push in this version; captured text/caption and metadata are preserved."])
        return "\n".join(parts)
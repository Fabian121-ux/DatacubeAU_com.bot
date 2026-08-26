from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog
from app.utils.time import utcnow


@dataclass(slots=True)
class RevocationResult:
    revoked_message_id: str
    matched: bool
    changed: bool
    message_id: int | None = None
    chat_id: str | None = None


class DeletedMessageService:
    """Durable WAHA message-revocation lifecycle over the existing messages table.

    This service never creates recovered content for a message Zina did not observe.
    It only marks an already-persisted Message as revoked and renders bounded owner-only
    evidence from that authoritative row.
    """

    DEFAULT_LIMIT = 1
    LIST_LIMIT = 10
    MAX_LIMIT = 20

    def __init__(self, session: AsyncSession):
        self.session = session

    async def record_revocation(self, event: dict[str, Any]) -> RevocationResult | None:
        payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
        revoked_id = self._revoked_message_id(payload)
        if not revoked_id:
            return None

        chat_id = self._revoked_chat_id(payload)
        params: dict[str, Any] = {"revoked_id": revoked_id}
        chat_clause = ""
        if chat_id:
            params["chat_id"] = chat_id
            chat_clause = " AND m.chat_id = :chat_id"

        row = (
            await self.session.execute(
                text(
                    """
                    SELECT m.id, m.chat_id, m.lifecycle_status, m.revoked_event_id
                    FROM messages m
                    WHERE (
                        m.source_message_id = :revoked_id
                        OR m.raw_payload_json->>'id' = :revoked_id
                    )
                    """
                    + chat_clause
                    + " ORDER BY m.id DESC LIMIT 1 FOR UPDATE"
                ),
                params,
            )
        ).mappings().first()

        event_id = self._clean_text(event.get("id"))
        revoked_at = self._event_time(event)
        metadata = self._metadata(payload)

        if row is None:
            self.session.add(
                AuditLog(
                    action="message_revocation_unmatched",
                    entity_type="message",
                    entity_id=revoked_id,
                    details_json={
                        "revoked_message_id": revoked_id,
                        "chat_id": chat_id,
                        "event_id": event_id,
                        "content_recovered": False,
                    },
                    created_at=utcnow(),
                )
            )
            await self.session.flush()
            return RevocationResult(revoked_message_id=revoked_id, matched=False, changed=False, chat_id=chat_id)

        already_revoked = str(row.get("lifecycle_status") or "").lower() == "revoked"
        same_event = bool(event_id and row.get("revoked_event_id") == event_id)
        changed = not already_revoked

        if not same_event:
            await self.session.execute(
                text(
                    """
                    UPDATE messages
                    SET source_message_id = COALESCE(source_message_id, :revoked_id),
                        lifecycle_status = 'revoked',
                        revoked_at = COALESCE(revoked_at, :revoked_at),
                        revoked_event_id = COALESCE(revoked_event_id, :event_id),
                        revoke_metadata_json = COALESCE(revoke_metadata_json, CAST(:metadata AS JSONB))
                    WHERE id = :message_id
                    """
                ),
                {
                    "message_id": int(row["id"]),
                    "revoked_id": revoked_id,
                    "revoked_at": revoked_at,
                    "event_id": event_id,
                    "metadata": self._json_text(metadata),
                },
            )

        if changed:
            self.session.add(
                AuditLog(
                    action="message_revoked",
                    entity_type="message",
                    entity_id=str(row["id"]),
                    details_json={
                        "revoked_message_id": revoked_id,
                        "chat_id": row.get("chat_id"),
                        "event_id": event_id,
                        "content_recovered": True,
                    },
                    created_at=utcnow(),
                )
            )
        await self.session.flush()
        return RevocationResult(
            revoked_message_id=revoked_id,
            matched=True,
            changed=changed,
            message_id=int(row["id"]),
            chat_id=str(row.get("chat_id") or "") or None,
        )

    async def render_command(self, args: str) -> str:
        mode, limit = self._parse_args(args)
        rows = (
            await self.session.execute(
                text(
                    """
                    SELECT
                        m.id,
                        m.chat_id,
                        m.direction,
                        m.message_text,
                        m.message_type,
                        m.created_at,
                        m.revoked_at,
                        m.source_message_id,
                        c.display_name,
                        c.contact_name,
                        c.push_name,
                        c.normalized_phone,
                        c.whatsapp_id
                    FROM messages m
                    LEFT JOIN contacts c ON c.id = m.contact_id
                    WHERE m.lifecycle_status = 'revoked'
                      AND m.chat_type = 'dm'
                    ORDER BY m.revoked_at DESC NULLS LAST, m.id DESC
                    LIMIT :limit
                    """
                ),
                {"limit": limit},
            )
        ).mappings().all()

        if not rows:
            return (
                "No captured deleted DM messages.\n\n"
                "Zina can only show content that was observed and stored before WAHA reported the deletion."
            )

        if mode == "info":
            return self._render_info(rows[0])
        if limit == 1 and mode != "list":
            return self._render_one(rows[0])

        lines = [f"DELETED MESSAGES — {len(rows)} shown"]
        for index, row in enumerate(rows, start=1):
            sender = self._sender_label(row)
            text_value = self._content(row)
            deleted_at = self._format_time(row.get("revoked_at"))
            lines.append(f"\n{index}. {sender} — {deleted_at}\n{text_value}")
        lines.append("\nUse .dm info for full metadata on the newest captured deletion.")
        return "\n".join(lines)

    @classmethod
    def _parse_args(cls, args: str) -> tuple[str, int]:
        value = (args or "").strip().lower()
        if not value:
            return "latest", cls.DEFAULT_LIMIT
        if value == "info":
            return "info", 1
        if value == "list":
            return "list", cls.LIST_LIMIT
        try:
            limit = int(value)
        except ValueError as exc:
            raise ValueError("usage: .dm, .dm 5, .dm list, or .dm info") from exc
        if limit < 1 or limit > cls.MAX_LIMIT:
            raise ValueError(f"deleted-message limit must be between 1 and {cls.MAX_LIMIT}")
        return "list", limit

    @classmethod
    def _render_one(cls, row: Any) -> str:
        return (
            "🗑 DELETED MESSAGE\n\n"
            f"From: {cls._sender_label(row)}\n"
            f"Sent: {cls._format_time(row.get('created_at'))}\n"
            f"Deleted: {cls._format_time(row.get('revoked_at'))}\n"
            f"Type: {row.get('message_type') or 'unknown'}\n\n"
            f"{cls._content(row)}"
        )

    @classmethod
    def _render_info(cls, row: Any) -> str:
        return (
            "DELETED MESSAGE INFO\n\n"
            f"Database ID: {row.get('id')}\n"
            f"Source message ID: {row.get('source_message_id') or 'unknown'}\n"
            f"From: {cls._sender_label(row)}\n"
            f"Chat: {row.get('chat_id') or 'unknown'}\n"
            f"Direction: {row.get('direction') or 'unknown'}\n"
            f"Type: {row.get('message_type') or 'unknown'}\n"
            f"Sent: {cls._format_time(row.get('created_at'))}\n"
            f"Deleted: {cls._format_time(row.get('revoked_at'))}\n"
            "Media retained: no dedicated media archive in this version\n"
            "Recovery basis: original content observed by Zina before revocation"
        )

    @staticmethod
    def _sender_label(row: Any) -> str:
        return str(
            row.get("contact_name")
            or row.get("display_name")
            or row.get("push_name")
            or row.get("normalized_phone")
            or row.get("whatsapp_id")
            or "Unknown"
        )

    @staticmethod
    def _content(row: Any) -> str:
        text_value = str(row.get("message_text") or "").strip()
        if text_value:
            return text_value
        message_type = str(row.get("message_type") or "unknown")
        return f"(no text/caption captured; original type: {message_type})"

    @staticmethod
    def _format_time(value: Any) -> str:
        if isinstance(value, datetime):
            return value.isoformat()
        return str(value or "unknown")

    @classmethod
    def _revoked_message_id(cls, payload: dict[str, Any]) -> str | None:
        direct = cls._clean_text(payload.get("revokedMessageId"))
        if direct:
            return direct
        for key in ("before", "after"):
            candidate = payload.get(key)
            if isinstance(candidate, dict):
                found = cls._clean_text(candidate.get("id"))
                if found:
                    return found
        return None

    @classmethod
    def _revoked_chat_id(cls, payload: dict[str, Any]) -> str | None:
        for key in ("before", "after"):
            candidate = payload.get(key)
            if not isinstance(candidate, dict):
                continue
            nested_chat = candidate.get("chat") if isinstance(candidate.get("chat"), dict) else {}
            value = candidate.get("chatId") or nested_chat.get("id") or candidate.get("from")
            cleaned = cls._clean_text(value)
            if cleaned:
                return cleaned
        return None

    @staticmethod
    def _event_time(event: dict[str, Any]) -> datetime:
        raw = event.get("timestamp")
        try:
            number = float(raw)
            if number > 10_000_000_000:
                number /= 1000.0
            return datetime.fromtimestamp(number, tz=timezone.utc)
        except (TypeError, ValueError, OSError, OverflowError):
            return utcnow()

    @classmethod
    def _metadata(cls, payload: dict[str, Any]) -> dict[str, Any]:
        result: dict[str, Any] = {"revokedMessageId": cls._revoked_message_id(payload)}
        for key in ("before", "after"):
            value = payload.get(key)
            if not isinstance(value, dict):
                continue
            nested_chat = value.get("chat") if isinstance(value.get("chat"), dict) else {}
            result[key] = {
                "id": cls._clean_text(value.get("id")),
                "chat_id": cls._clean_text(value.get("chatId") or nested_chat.get("id") or value.get("from")),
                "type": cls._clean_text(value.get("type")),
                "from_me": value.get("fromMe") if isinstance(value.get("fromMe"), bool) else None,
                "has_media": value.get("hasMedia") if isinstance(value.get("hasMedia"), bool) else None,
            }
        return result

    @staticmethod
    def _json_text(value: dict[str, Any]) -> str:
        import json

        return json.dumps(value, separators=(",", ":"), ensure_ascii=False)

    @staticmethod
    def _clean_text(value: Any) -> str | None:
        if value is None:
            return None
        text_value = str(value).strip()
        return text_value or None

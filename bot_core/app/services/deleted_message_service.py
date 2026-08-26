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
    evidence from that authoritative row. If a revoke reaches Zina just before the
    corresponding normal message transaction commits, the unmatched revoke remains as
    durable AuditLog evidence and is reconciled when that message event finishes.
    """

    DEFAULT_LIMIT = 1
    LIST_LIMIT = 10
    MAX_LIMIT = 20
    MAX_ENTRY_CONTENT_CHARS = 900
    MAX_REPLY_CHARS = 3500

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
                        OR m.raw_payload_json->'message'->>'id' = :revoked_id
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
                        "revoked_at": revoked_at.isoformat(),
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

    async def reconcile_pending_for_message(
        self,
        *,
        source_message_id: str,
        chat_id: str | None,
    ) -> bool:
        """Apply a previously unmatched revoke once the original Message exists.

        WAHA can deliver independent webhook events close together. If `message.revoked`
        wins the race against the normal `message` commit, `record_revocation` keeps a
        compact unmatched audit record rather than synthesizing deleted content. The
        event gateway and durable reconciliation worker call this method after normal
        message persistence so the original can inherit the earlier revoke lifecycle.
        """
        source_message_id = (source_message_id or "").strip()
        if not source_message_id:
            return False

        params: dict[str, Any] = {"source_id": source_message_id}
        chat_clause = ""
        if chat_id:
            params["chat_id"] = chat_id
            chat_clause = " AND m.chat_id = :chat_id"

        message = (
            await self.session.execute(
                text(
                    """
                    SELECT m.id, m.chat_id, m.lifecycle_status
                    FROM messages m
                    WHERE (
                        m.source_message_id = :source_id
                        OR m.raw_payload_json->>'id' = :source_id
                        OR m.raw_payload_json->'message'->>'id' = :source_id
                    )
                    """
                    + chat_clause
                    + " ORDER BY m.id DESC LIMIT 1 FOR UPDATE"
                ),
                params,
            )
        ).mappings().first()
        if message is None or str(message.get("lifecycle_status") or "active").lower() == "revoked":
            return False

        audit_params: dict[str, Any] = {"source_id": source_message_id}
        audit_chat_clause = ""
        if chat_id:
            audit_params["chat_id"] = chat_id
            audit_chat_clause = " AND (a.details_json->>'chat_id' IS NULL OR a.details_json->>'chat_id' = :chat_id)"
        pending = (
            await self.session.execute(
                text(
                    """
                    SELECT a.id, a.created_at, a.details_json
                    FROM audit_logs a
                    WHERE a.action = 'message_revocation_unmatched'
                      AND a.details_json->>'revoked_message_id' = :source_id
                    """
                    + audit_chat_clause
                    + " ORDER BY a.created_at DESC, a.id DESC LIMIT 1"
                ),
                audit_params,
            )
        ).mappings().first()
        if pending is None:
            return False

        details = pending.get("details_json") if isinstance(pending.get("details_json"), dict) else {}
        revoked_at = self._parse_datetime(details.get("revoked_at")) or pending.get("created_at") or utcnow()
        event_id = self._clean_text(details.get("event_id"))
        metadata = {
            "revokedMessageId": source_message_id,
            "late_reconciled": True,
            "source_unmatched_audit_id": int(pending["id"]),
        }
        await self.session.execute(
            text(
                """
                UPDATE messages
                SET source_message_id = COALESCE(source_message_id, :source_id),
                    lifecycle_status = 'revoked',
                    revoked_at = COALESCE(revoked_at, :revoked_at),
                    revoked_event_id = COALESCE(revoked_event_id, :event_id),
                    revoke_metadata_json = COALESCE(revoke_metadata_json, CAST(:metadata AS JSONB))
                WHERE id = :message_id
                  AND lifecycle_status <> 'revoked'
                """
            ),
            {
                "message_id": int(message["id"]),
                "source_id": source_message_id,
                "revoked_at": revoked_at,
                "event_id": event_id,
                "metadata": self._json_text(metadata),
            },
        )
        self.session.add(
            AuditLog(
                action="message_revocation_late_reconciled",
                entity_type="message",
                entity_id=str(message["id"]),
                details_json={
                    "revoked_message_id": source_message_id,
                    "chat_id": message.get("chat_id"),
                    "source_unmatched_audit_id": int(pending["id"]),
                    "content_recovered": True,
                },
                created_at=utcnow(),
            )
        )
        await self.session.flush()
        return True

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
            return self._bound_reply(self._render_info(rows[0]))
        if limit == 1 and mode != "list":
            return self._bound_reply(self._render_one(rows[0]))

        lines = [f"DELETED MESSAGES — {len(rows)} shown"]
        for index, row in enumerate(rows, start=1):
            sender = self._sender_label(row)
            text_value = self._truncate(self._content(row), self.MAX_ENTRY_CONTENT_CHARS)
            deleted_at = self._format_time(row.get("revoked_at"))
            candidate = "\n".join([*lines, f"\n{index}. {sender} — {deleted_at}\n{text_value}"])
            if len(candidate) > self.MAX_REPLY_CHARS - 120:
                lines.append("\n…more deleted messages omitted to keep this WhatsApp reply within the safe size limit.")
                break
            lines.append(f"\n{index}. {sender} — {deleted_at}\n{text_value}")
        lines.append("\nUse .dm info for full metadata on the newest captured deletion.")
        return self._bound_reply("\n".join(lines))

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
        content = cls._truncate(cls._content(row), cls.MAX_ENTRY_CONTENT_CHARS)
        return (
            "🗑 DELETED MESSAGE\n\n"
            f"From: {cls._sender_label(row)}\n"
            f"Sent: {cls._format_time(row.get('created_at'))}\n"
            f"Deleted: {cls._format_time(row.get('revoked_at'))}\n"
            f"Type: {row.get('message_type') or 'unknown'}\n\n"
            f"{content}"
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

    @classmethod
    def _bound_reply(cls, value: str) -> str:
        return cls._truncate(value, cls.MAX_REPLY_CHARS)

    @staticmethod
    def _truncate(value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        if limit <= 1:
            return value[:limit]
        return value[: limit - 1].rstrip() + "…"

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

    @staticmethod
    def _parse_datetime(value: Any) -> datetime | None:
        if isinstance(value, datetime):
            return value
        if not isinstance(value, str) or not value.strip():
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed

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

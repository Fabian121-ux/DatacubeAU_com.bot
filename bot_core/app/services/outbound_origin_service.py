from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, OutboundMessage
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.time import utcnow


class OutboundOriginService:
    """Identify WAHA ``fromMe`` echoes produced by Zina's outbound queue.

    Completed sends are correlated by the exact WAHA transport message ID recorded in
    append-only ``outbound_queue_sent`` audits. During the smaller send/timeout race,
    Zina asks WAHA for the *specific* webhook message ID and compares that concrete
    message to recent queue attempts for the same chat. This avoids suppressing an
    unrelated Fabian-authored message merely because another row happens to be
    ``sending`` in that chat.
    """

    MAX_RECENT_DELIVERIES = 200
    ATTEMPT_WINDOW = timedelta(minutes=5)
    MAX_ATTEMPT_ROWS = 20
    _ID_KEYS = frozenset({"id", "messageid", "message_id", "serialized", "_serialized"})
    _TEXT_TYPES = frozenset({"text", "chat", "conversation"})
    _AMBIGUOUS_ERROR_MARKERS = (
        "timeout",
        "timed out",
        "readtimeout",
        "writetimeout",
        "connecttimeout",
        "requesterror",
        "connection reset",
        "connection aborted",
        "connection closed",
        "server disconnected",
    )

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_zina_originated(
        self,
        *,
        chat_id: str,
        transport_message_id: str | None,
    ) -> bool:
        wanted = (transport_message_id or "").strip()
        chat = (chat_id or "").strip()
        if not chat or not wanted:
            return False

        if await self._matches_completed_delivery(chat=chat, wanted=wanted):
            return True

        # An early ``message.any`` can arrive before sendText/sendImage returns, while
        # an accepted request can later surface as a timeout. In both cases the queue
        # does not yet have a successful transport-ID audit. Resolve the *specific*
        # WAHA message by ID and require its payload/timestamp to match a recent queue
        # attempt. If WAHA cannot resolve the ID, do not suppress Fabian activity.
        remote = await self._fetch_waha_message(chat=chat, wanted=wanted)
        if not remote:
            return False
        return await self._matches_recent_attempt(chat=chat, remote=remote)

    async def _matches_completed_delivery(self, *, chat: str, wanted: str) -> bool:
        # Filter by entity/chat in SQL before the bound so busy traffic in other chats
        # cannot push the matching delivery out of the candidate window.
        rows = (
            await self.session.execute(
                select(AuditLog)
                .where(
                    AuditLog.action == "outbound_queue_sent",
                    AuditLog.entity_type == "outbound_queue",
                    AuditLog.details_json["chat_id"].as_string() == chat,
                )
                .order_by(AuditLog.id.desc())
                .limit(self.MAX_RECENT_DELIVERIES)
            )
        ).scalars().all()

        for row in rows:
            details = row.details_json if isinstance(row.details_json, dict) else {}
            if wanted in self._transport_ids(details.get("waha_response")):
                return True
        return False

    async def _fetch_waha_message(self, *, chat: str, wanted: str) -> dict[str, Any] | None:
        client = WAHAClient()
        try:
            payload = await client.get_chat_message(chat_id=chat, message_id=wanted)
        except WahaClientError:
            return None
        finally:
            await client.close()
        return payload if isinstance(payload, dict) else None

    async def _matches_recent_attempt(self, *, chat: str, remote: dict[str, Any]) -> bool:
        remote_text = self._message_text(remote)
        remote_type = self._message_type(remote)
        remote_has_media = self._message_has_media(remote, remote_type)
        remote_timestamp = self._message_timestamp(remote)
        if remote_text is None and not remote_has_media:
            return False

        cutoff = utcnow() - self.ATTEMPT_WINDOW
        rows = (
            await self.session.execute(
                select(OutboundMessage)
                .where(
                    OutboundMessage.chat_id == chat,
                    OutboundMessage.status.in_(("sending", "retrying", "failed")),
                    OutboundMessage.updated_at >= cutoff,
                )
                .order_by(OutboundMessage.updated_at.desc(), OutboundMessage.id.desc())
                .limit(self.MAX_ATTEMPT_ROWS)
            )
        ).scalars().all()

        for row in rows:
            # Post-send retrying/failed rows are origin evidence only for transport-
            # ambiguous failures. Definitive HTTP errors cannot justify suppressing a
            # real Fabian message with coincidentally identical text.
            if row.status in {"retrying", "failed"} and not self._is_ambiguous_failure(row.error_message):
                continue
            if not self._payload_matches(row, remote_text, remote_type, remote_has_media):
                continue
            if remote_timestamp is not None and row.updated_at is not None:
                row_time = self._as_utc(row.updated_at)
                if abs((remote_timestamp - row_time).total_seconds()) > self.ATTEMPT_WINDOW.total_seconds():
                    continue
            return True
        return False

    @classmethod
    def _payload_matches(
        cls,
        row: OutboundMessage,
        remote_text: str | None,
        remote_type: str,
        remote_has_media: bool,
    ) -> bool:
        expected_media = bool(row.media_url)
        if expected_media != remote_has_media:
            return False
        expected_text = (row.media_caption or row.message_text) if expected_media else row.message_text
        if (remote_text or "") != (expected_text or ""):
            return False
        if not expected_media:
            return remote_type in cls._TEXT_TYPES
        # WAHA engines can use concrete media types (image/video/document/sticker) or
        # generic media values. Presence of media plus exact caption/body is the stable
        # cross-engine contract; when a concrete type is available, enforce it.
        expected_type = (row.media_type or "").strip().lower()
        if expected_type and remote_type not in {expected_type, "media"}:
            return False
        return True

    @classmethod
    def _is_ambiguous_failure(cls, error: str | None) -> bool:
        text = (error or "").lower()
        return any(marker in text for marker in cls._AMBIGUOUS_ERROR_MARKERS)

    @classmethod
    def _message_text(cls, payload: dict[str, Any]) -> str | None:
        data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
        for value in (
            payload.get("body"),
            payload.get("text"),
            payload.get("caption"),
            data.get("body"),
            data.get("caption"),
        ):
            if value is not None:
                return str(value)
        return None

    @classmethod
    def _message_type(cls, payload: dict[str, Any]) -> str:
        data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
        return str(payload.get("type") or data.get("type") or "text").strip().lower()

    @classmethod
    def _message_has_media(cls, payload: dict[str, Any], message_type: str) -> bool:
        data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
        explicit = payload.get("hasMedia")
        if explicit is None:
            explicit = data.get("hasMedia")
        if isinstance(explicit, bool):
            return explicit
        return message_type not in cls._TEXT_TYPES

    @classmethod
    def _message_timestamp(cls, payload: dict[str, Any]) -> datetime | None:
        data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
        raw = payload.get("timestamp") or payload.get("t") or data.get("t") or data.get("timestamp")
        if raw is None:
            return None
        if isinstance(raw, (int, float)):
            value = float(raw)
            if value > 10_000_000_000:
                value /= 1000.0
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc)
            except (OverflowError, OSError, ValueError):
                return None
        if isinstance(raw, str):
            text = raw.strip().replace("Z", "+00:00")
            try:
                parsed = datetime.fromisoformat(text)
            except ValueError:
                return None
            return cls._as_utc(parsed)
        return None

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)

    @classmethod
    def _transport_ids(cls, value: Any) -> set[str]:
        found: set[str] = set()
        cls._collect_transport_ids(value, found)
        return found

    @classmethod
    def _collect_transport_ids(cls, value: Any, found: set[str]) -> None:
        if isinstance(value, dict):
            for raw_key, nested in value.items():
                key = str(raw_key).lower().replace("-", "_")
                if key in cls._ID_KEYS:
                    cls._add_scalar_ids(nested, found)
                cls._collect_transport_ids(nested, found)
        elif isinstance(value, (list, tuple)):
            for nested in value:
                cls._collect_transport_ids(nested, found)

    @staticmethod
    def _add_scalar_ids(value: Any, found: set[str]) -> None:
        if isinstance(value, (str, int)):
            text = str(value).strip()
            if text:
                found.add(text)
        elif isinstance(value, dict):
            for nested in value.values():
                if isinstance(nested, (str, int)):
                    text = str(nested).strip()
                    if text:
                        found.add(text)
        elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
            for nested in value:
                if isinstance(nested, (str, int)):
                    text = str(nested).strip()
                    if text:
                        found.add(text)

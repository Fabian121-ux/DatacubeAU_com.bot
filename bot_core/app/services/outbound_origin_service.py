from __future__ import annotations

from collections.abc import Iterable
from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog, OutboundMessage
from app.utils.time import utcnow


class OutboundOriginService:
    """Identify WAHA `fromMe` echoes produced by Zina's outbound queue.

    There are two evidence windows to handle:

    1. After WAHA returns, append-only ``outbound_queue_sent`` audit evidence carries
       the transport message ID and is the strongest origin proof.
    2. During the send itself, WAHA may emit ``message.any`` *before* the HTTP request
       has returned (or after WhatsApp accepted it while the client later times out).
       At that point no transport ID has been persisted yet, but the authoritative
       outbound row has already been committed as ``sending`` by the worker. A recent
       in-flight row for the same chat is therefore treated conservatively as Zina
       origin so an API echo cannot resume Fabian or cancel takeover.

    The in-flight fallback is deliberately short-lived and bounded. In the ambiguous
    race window it is safer to ignore a possible owner-activity signal than to let a
    bot-generated echo terminate an active assisted conversation.
    """

    MAX_RECENT_DELIVERIES = 200
    IN_FLIGHT_ECHO_WINDOW = timedelta(minutes=5)
    MAX_IN_FLIGHT_ROWS = 10
    _ID_KEYS = frozenset({"id", "messageid", "message_id", "serialized", "_serialized"})

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
        if not chat:
            return False

        if wanted and await self._matches_completed_delivery(chat=chat, wanted=wanted):
            return True

        # The outbound worker commits status='sending' *before* calling WAHA. That is
        # the only durable evidence guaranteed to exist if WAHA emits the fromMe event
        # before sendText/sendImage returns, and it also covers accepted-but-timeout
        # ambiguity. Never use pending/retrying rows here: only a worker-owned active
        # send may suppress owner-activity handling.
        cutoff = utcnow() - self.IN_FLIGHT_ECHO_WINDOW
        rows = (
            await self.session.execute(
                select(OutboundMessage.id)
                .where(
                    OutboundMessage.chat_id == chat,
                    OutboundMessage.status == "sending",
                    OutboundMessage.updated_at >= cutoff,
                )
                .order_by(OutboundMessage.updated_at.desc(), OutboundMessage.id.desc())
                .limit(self.MAX_IN_FLIGHT_ROWS)
            )
        ).scalars().all()
        return bool(rows)

    async def _matches_completed_delivery(self, *, chat: str, wanted: str) -> bool:
        rows = (
            await self.session.execute(
                select(AuditLog)
                .where(AuditLog.action == "outbound_queue_sent")
                .order_by(AuditLog.id.desc())
                .limit(self.MAX_RECENT_DELIVERIES)
            )
        ).scalars().all()

        for row in rows:
            details = row.details_json if isinstance(row.details_json, dict) else {}
            if str(details.get("chat_id") or "").strip() != chat:
                continue
            response = details.get("waha_response")
            if wanted in self._transport_ids(response):
                return True
        return False

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

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog


class OutboundOriginService:
    """Identify WAHA ``fromMe`` echoes produced by Zina's outbound queue.

    WAHA's ``message.any`` payload carries a causal ``source`` field: ``api`` when
    the message was created through the WAHA API and ``app`` when it was authored
    in WhatsApp itself. That transport-origin evidence is the primary guard during
    the send/echo race. Completed sends are also correlated by the exact persisted
    WAHA transport message ID so older events and engines that omit ``source`` can
    still be recognized without guessing from message content or timestamps.
    """

    MAX_RECENT_DELIVERIES = 200
    _ID_KEYS = frozenset({"id", "messageid", "message_id", "serialized", "_serialized"})

    def __init__(self, session: AsyncSession):
        self.session = session

    async def is_zina_originated(
        self,
        *,
        chat_id: str,
        transport_message_id: str | None,
        transport_source: str | None = None,
    ) -> bool:
        wanted = (transport_message_id or "").strip()
        chat = (chat_id or "").strip()
        if not chat or not wanted:
            return False

        source = (transport_source or "").strip().lower()

        # WAHA documents ``source=api`` for messages created via its API and
        # ``source=app`` for messages authored in WhatsApp. In this fromMe-only
        # call path, ``api`` is causal evidence that the event is a Zina/API echo;
        # unlike payload/time matching, it cannot swallow a same-text Fabian reply.
        if source == "api":
            return True

        if await self._matches_completed_delivery(chat=chat, wanted=wanted):
            return True

        # Do not infer origin from text/caption/timestamp similarity. If WAHA marks
        # the event as app-authored, or omits source and there is no exact completed
        # transport-ID match, preserve the owner event rather than risking a false
        # suppression. This deliberately prefers an occasional duplicate takeover
        # transition on legacy engines over dropping a real Fabian command/reply.
        return False

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

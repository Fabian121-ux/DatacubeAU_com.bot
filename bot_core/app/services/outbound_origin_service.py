from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog
from app.services.waha_client import WAHAClient, WahaClientError


class OutboundOriginService:
    """Identify WAHA ``fromMe`` echoes produced by Zina's outbound queue.

    Completed sends are correlated by the exact WAHA transport message ID persisted
    in ``outbound_queue_sent`` audits. During the earlier send/echo race, Zina fetches
    that exact WAHA message and uses WAHA's causal ``source`` field: ``api`` means the
    message was created through the WAHA API, while ``app`` means it was authored in
    WhatsApp itself. Zina never infers origin from matching text, caption, or time.
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

        if await self._matches_completed_delivery(chat=chat, wanted=wanted):
            return True

        source = (transport_source or "").strip().lower()
        if not source:
            source = await self._fetch_transport_source(chat=chat, wanted=wanted)

        # WAHA documents `source=api` for API-created outgoing messages and
        # `source=app` for WhatsApp-authored messages. This is causal evidence;
        # payload/time similarity is not. Unknown/legacy source is deliberately
        # preserved as owner activity rather than risking a false suppression.
        return source == "api"

    async def _fetch_transport_source(self, *, chat: str, wanted: str) -> str:
        client = WAHAClient()
        try:
            payload = await client.get_chat_message(chat_id=chat, message_id=wanted)
        except WahaClientError:
            return ""
        finally:
            await client.close()
        if not isinstance(payload, dict):
            return ""
        data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
        return str(payload.get("source") or data.get("source") or "").strip().lower()

    async def _matches_completed_delivery(self, *, chat: str, wanted: str) -> bool:
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

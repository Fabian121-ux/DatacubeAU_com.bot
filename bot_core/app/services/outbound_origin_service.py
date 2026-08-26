from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import AuditLog


class OutboundOriginService:
    """Identify WAHA `fromMe` echoes that were produced by Zina's outbound queue.

    Successful queue delivery already records the WAHA response in append-only audit
    evidence. Reuse that evidence instead of creating a second transport-ID store.
    The lookup is deliberately bounded because it runs only for owner-authored/fromMe
    events and should never scan lifetime audit history.
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
    ) -> bool:
        wanted = (transport_message_id or "").strip()
        chat = (chat_id or "").strip()
        if not wanted or not chat:
            return False

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

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import OutboundMessage
from app.utils.time import utcnow


@dataclass(frozen=True, slots=True)
class OutboundSafetyDecision:
    allowed: bool
    reason: str


class OutboundSafetyLimitService:
    """Durable fail-closed safety limits for non-owner outbound delivery.

    The delivery worker is the only caller. A transaction-scoped PostgreSQL advisory
    lock serializes safety reservations across worker instances. `sending` rows count
    as recent reservations so one batch cannot burst past the configured ceilings.
    """

    GLOBAL_LOCK_KEY = 910200001
    PER_CONTACT_PER_MINUTE = 3
    GLOBAL_PER_MINUTE = 20
    PER_CONTACT_ACTIVE_BACKLOG = 10
    GLOBAL_ACTIVE_BACKLOG = 50
    WINDOW = timedelta(minutes=1)
    ACTIVE_STATUSES = ("pending", "retrying", "sending")

    def __init__(self, session: AsyncSession):
        self.session = session

    async def authorize(self, message: OutboundMessage, *, now: datetime | None = None) -> OutboundSafetyDecision:
        instant = now or utcnow()
        chat_id = str(message.chat_id or "").strip()
        if not chat_id or getattr(message, "id", None) is None:
            return OutboundSafetyDecision(False, "outbound safety context missing exact queue/chat identity")

        await self.session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_key)"),
            {"lock_key": self.GLOBAL_LOCK_KEY},
        )

        global_backlog = await self._count(
            OutboundMessage.status.in_(self.ACTIVE_STATUSES),
        )
        if global_backlog > self.GLOBAL_ACTIVE_BACKLOG:
            return OutboundSafetyDecision(False, "global outbound queue backpressure limit exceeded")

        contact_backlog = await self._count(
            OutboundMessage.status.in_(self.ACTIVE_STATUSES),
            OutboundMessage.chat_id == chat_id,
        )
        if contact_backlog > self.PER_CONTACT_ACTIVE_BACKLOG:
            return OutboundSafetyDecision(False, "per-contact outbound queue backpressure limit exceeded")

        window_start = instant - self.WINDOW
        global_recent = await self._count(
            OutboundMessage.status.in_(("sent", "sending")),
            OutboundMessage.updated_at >= window_start,
            OutboundMessage.id != int(message.id),
        )
        if global_recent >= self.GLOBAL_PER_MINUTE:
            return OutboundSafetyDecision(False, "global outbound safety rate limit reached")

        contact_recent = await self._count(
            OutboundMessage.status.in_(("sent", "sending")),
            OutboundMessage.updated_at >= window_start,
            OutboundMessage.chat_id == chat_id,
            OutboundMessage.id != int(message.id),
        )
        if contact_recent >= self.PER_CONTACT_PER_MINUTE:
            return OutboundSafetyDecision(False, "per-contact outbound safety rate limit reached")

        return OutboundSafetyDecision(True, "outbound safety limits allow delivery")

    async def _count(self, *filters) -> int:
        stmt = select(func.count()).select_from(OutboundMessage)
        for condition in filters:
            stmt = stmt.where(condition)
        value = (await self.session.execute(stmt)).scalar_one()
        return int(value or 0)

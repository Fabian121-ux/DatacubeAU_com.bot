"""Rate limiting: per-user daily, per-user cooldown, and global AI daily cap."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Direction
from app.models.schema import AICall, Message
from app.services.bot_config_service import BotConfigService
from app.utils.time import utcnow


class RateLimitResult:
    __slots__ = ("allowed", "reason")

    def __init__(self, allowed: bool, reason: str = ""):
        self.allowed = allowed
        self.reason = reason


class RateLimiter:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = BotConfigService(session)

    async def check_user_daily_limit(self, contact_id: int) -> RateLimitResult:
        limit = await self.config.get_int("rate_limit_per_user_daily", 50)
        if limit <= 0:
            return RateLimitResult(True)

        today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count(Message.id))
            .where(Message.contact_id == contact_id)
            .where(Message.direction == Direction.OUTBOUND.value)
            .where(Message.created_at >= today_start)
        )
        count = (await self.session.execute(stmt)).scalar_one()
        if count >= limit:
            return RateLimitResult(False, f"daily limit reached ({count}/{limit})")
        return RateLimitResult(True)

    async def check_global_ai_limit(self) -> RateLimitResult:
        limit = await self.config.get_int("rate_limit_global_daily", 500)
        if limit <= 0:
            return RateLimitResult(True)

        today_start = utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        stmt = (
            select(func.count(AICall.id))
            .where(AICall.created_at >= today_start)
        )
        count = (await self.session.execute(stmt)).scalar_one()
        if count >= limit:
            return RateLimitResult(False, f"global AI daily limit reached ({count}/{limit})")
        return RateLimitResult(True)

    async def check_message_cooldown(self, chat_id: str) -> RateLimitResult:
        cooldown = await self.config.get_int("rate_limit_cooldown_seconds", 6)
        if cooldown <= 0:
            return RateLimitResult(True)

        cutoff = utcnow() - timedelta(seconds=cooldown)
        stmt = (
            select(Message.id)
            .where(Message.chat_id == chat_id)
            .where(Message.direction == Direction.OUTBOUND.value)
            .where(Message.created_at >= cutoff)
            .limit(1)
        )
        recent = (await self.session.execute(stmt)).scalar_one_or_none()
        if recent is not None:
            return RateLimitResult(False, "message cooldown active")
        return RateLimitResult(True)

"""Rate limiting: per-user daily, per-user cooldown, and global AI daily cap."""
from __future__ import annotations

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.enums import Direction
from app.models.schema import AICall, AIUsageEvent, AIUsageQuota, Message
from app.services.bot_config_service import BotConfigService
from app.utils.time import utcnow


class RateLimitResult:
    __slots__ = ("allowed", "reason", "limit", "used", "reset_time")

    def __init__(self, allowed: bool, reason: str = "", *, limit: int = 0, used: int = 0, reset_time=None):
        self.allowed = allowed
        self.reason = reason
        self.limit = limit
        self.used = used
        self.reset_time = reset_time


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

    async def check_user_ai_quota(self, contact_id: int) -> RateLimitResult:
        limit = await self.config.get_int("ai_quota_per_user_daily", 5)
        if limit <= 0:
            return RateLimitResult(True, limit=limit)

        quota = await self._get_or_create_ai_quota(contact_id)
        await self._reset_quota_if_due(quota)
        if quota.usage_count >= limit:
            return RateLimitResult(
                False,
                f"user AI quota reached ({quota.usage_count}/{limit})",
                limit=limit,
                used=quota.usage_count,
                reset_time=quota.reset_time,
            )
        return RateLimitResult(True, limit=limit, used=quota.usage_count, reset_time=quota.reset_time)

    async def record_ai_usage(self, contact_id: int, ai_call: AICall, *, response_source: str) -> AIUsageEvent:
        quota = await self._get_or_create_ai_quota(contact_id)
        await self._reset_quota_if_due(quota)
        quota.usage_count += 1
        quota.updated_at = utcnow()
        total_tokens = int(ai_call.prompt_tokens or 0) + int(ai_call.completion_tokens or 0)
        event = AIUsageEvent(
            contact_id=contact_id,
            ai_call_id=ai_call.id,
            model=ai_call.model,
            mode=ai_call.mode,
            prompt_tokens=int(ai_call.prompt_tokens or 0),
            completion_tokens=int(ai_call.completion_tokens or 0),
            total_tokens=total_tokens,
            response_source=response_source[:40],
        )
        self.session.add(event)
        await self.session.flush()
        return event

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

    async def _get_or_create_ai_quota(self, contact_id: int) -> AIUsageQuota:
        stmt = select(AIUsageQuota).where(AIUsageQuota.contact_id == contact_id).limit(1)
        quota = (await self.session.execute(stmt)).scalar_one_or_none()
        if quota:
            return quota
        quota = AIUsageQuota(contact_id=contact_id, usage_count=0, reset_time=self._next_reset_time())
        self.session.add(quota)
        await self.session.flush()
        return quota

    async def _reset_quota_if_due(self, quota: AIUsageQuota) -> None:
        if quota.reset_time > utcnow():
            return
        quota.usage_count = 0
        quota.reset_time = self._next_reset_time()
        quota.updated_at = utcnow()
        await self.session.flush()

    @staticmethod
    def _next_reset_time():
        now = utcnow()
        tomorrow = now + timedelta(days=1)
        return tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)

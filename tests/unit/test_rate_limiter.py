from __future__ import annotations

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.schema import AICall, AIUsageEvent, AIUsageQuota
from app.services.rate_limiter import RateLimiter
from app.utils.time import utcnow


@pytest.mark.asyncio
async def test_user_ai_quota_enforcement_reset_and_usage_tracking(db_session, test_contact) -> None:
    limiter = RateLimiter(db_session)
    await limiter.config.set("ai_quota_per_user_daily", "5")

    initial = await limiter.check_user_ai_quota(test_contact.id)
    quota = (
        await db_session.execute(select(AIUsageQuota).where(AIUsageQuota.contact_id == test_contact.id))
    ).scalar_one()

    assert initial.allowed is True
    assert initial.limit == 5
    assert quota.usage_count == 0

    quota.usage_count = 5
    quota.reset_time = utcnow() + timedelta(hours=2)
    blocked = await limiter.check_user_ai_quota(test_contact.id)

    assert blocked.allowed is False
    assert blocked.used == 5

    quota.reset_time = utcnow() - timedelta(seconds=1)
    reset = await limiter.check_user_ai_quota(test_contact.id)

    assert reset.allowed is True
    assert quota.usage_count == 0

    ai_call = AICall(
        prompt_hash="hash",
        mode="light",
        model="test-model",
        prompt_tokens=11,
        completion_tokens=7,
        latency_ms=12,
        success=True,
    )
    db_session.add(ai_call)
    await db_session.flush()

    event = await limiter.record_ai_usage(test_contact.id, ai_call, response_source="AI")
    rows = (await db_session.execute(select(AIUsageEvent))).scalars().all()

    assert event.total_tokens == 18
    assert quota.usage_count == 1
    assert len(rows) == 1
    assert rows[0].model == "test-model"

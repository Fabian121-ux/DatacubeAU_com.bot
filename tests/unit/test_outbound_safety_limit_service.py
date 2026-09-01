from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.schema import OutboundMessage
from app.services.outbound_safety_limit_service import OutboundSafetyLimitService
from app.utils.time import utcnow


def _row(*, chat_id: str, status: str, updated_at=None, text: str = "test") -> OutboundMessage:
    instant = updated_at or utcnow()
    return OutboundMessage(
        chat_id=chat_id,
        message_text=text,
        status=status,
        retry_count=0,
        max_retries=3,
        next_attempt_at=instant,
        updated_at=instant,
    )


@pytest.mark.asyncio
async def test_per_contact_rate_limit_fails_closed(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="222@c.us", status="sent", updated_at=now, text=f"prior-{index}")
            for index in range(3)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound safety rate limit reached"


@pytest.mark.asyncio
async def test_global_rate_limit_fails_closed(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(
                chat_id=f"{300 + index}@c.us",
                status="sent",
                updated_at=now,
                text=f"global-prior-{index}",
            )
            for index in range(20)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "global outbound safety rate limit reached"


@pytest.mark.asyncio
async def test_sending_rows_reserve_rate_capacity(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="222@c.us", status="sending", updated_at=now, text=f"reserved-{index}")
            for index in range(3)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound safety rate limit reached"


@pytest.mark.asyncio
async def test_per_contact_active_backlog_overflow_fails_closed(db_session):
    old = utcnow() - timedelta(minutes=5)
    current = _row(chat_id="222@c.us", status="pending", updated_at=old, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="222@c.us", status="pending", updated_at=old, text=f"backlog-{index}")
            for index in range(10)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=utcnow())

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound queue backpressure limit exceeded"


@pytest.mark.asyncio
async def test_global_active_backlog_overflow_fails_closed(db_session):
    old = utcnow() - timedelta(minutes=5)
    current = _row(chat_id="222@c.us", status="pending", updated_at=old, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(
                chat_id=f"{400 + index}@c.us",
                status="pending",
                updated_at=old,
                text=f"global-backlog-{index}",
            )
            for index in range(50)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=utcnow())

    assert decision.allowed is False
    assert decision.reason == "global outbound queue backpressure limit exceeded"


@pytest.mark.asyncio
async def test_below_limits_allows_exact_queue_row(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="222@c.us", status="sent", updated_at=now, text=f"prior-{index}")
            for index in range(2)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is True
    assert decision.reason == "outbound safety limits allow delivery"

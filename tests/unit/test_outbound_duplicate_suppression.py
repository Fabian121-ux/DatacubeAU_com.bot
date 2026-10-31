from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.schema import OutboundMessage
from app.services.outbound_safety_limit_service import OutboundSafetyLimitService
from app.utils.time import utcnow


def _row(*, chat_id: str, text: str, status: str, updated_at) -> OutboundMessage:
    return OutboundMessage(
        chat_id=chat_id,
        message_text=text,
        status=status,
        retry_count=0,
        max_retries=3,
        next_attempt_at=updated_at,
        updated_at=updated_at,
    )


@pytest.mark.asyncio
async def test_recent_canonical_duplicate_same_contact_is_suppressed(db_session):
    now = utcnow()
    sent = _row(chat_id="222@c.us", text="Hello, Amanda!", status="sent", updated_at=now)
    current = _row(chat_id="222@c.us", text="hello amanda", status="pending", updated_at=now)
    db_session.add_all([sent, current])
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "recent duplicate/similar outbound content suppressed"


@pytest.mark.asyncio
async def test_duplicate_suppression_never_crosses_contacts(db_session):
    now = utcnow()
    db_session.add(_row(chat_id="111@c.us", text="same content", status="sent", updated_at=now))
    current = _row(chat_id="222@c.us", text="same content", status="pending", updated_at=now)
    db_session.add(current)
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is True


@pytest.mark.asyncio
async def test_old_same_contact_content_outside_window_is_allowed(db_session):
    now = utcnow()
    db_session.add(
        _row(
            chat_id="222@c.us",
            text="same content",
            status="sent",
            updated_at=now - timedelta(minutes=11),
        )
    )
    current = _row(chat_id="222@c.us", text="same content", status="pending", updated_at=now)
    db_session.add(current)
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is True


@pytest.mark.asyncio
async def test_different_content_same_contact_is_allowed_below_limits(db_session):
    now = utcnow()
    db_session.add(_row(chat_id="222@c.us", text="first answer", status="sent", updated_at=now))
    current = _row(chat_id="222@c.us", text="second answer", status="pending", updated_at=now)
    db_session.add(current)
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is True

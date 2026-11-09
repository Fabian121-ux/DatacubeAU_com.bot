from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.schema import Contact, OutboundMessage
from app.services.outbound_safety_limit_service import OutboundSafetyLimitService
from app.utils.time import utcnow


def _row(
    *,
    chat_id: str,
    status: str,
    updated_at=None,
    text: str = "test",
    media_url: str | None = None,
    media_type: str | None = None,
    media_caption: str | None = None,
    formatting_json: dict | None = None,
) -> OutboundMessage:
    instant = updated_at or utcnow()
    return OutboundMessage(
        chat_id=chat_id,
        message_text=text,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        formatting_json=formatting_json or {},
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


@pytest.mark.asyncio
async def test_stale_sending_rows_still_reserve_per_contact_rate_capacity(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(
                chat_id="222@c.us",
                status="sending",
                updated_at=now - timedelta(minutes=3),
                text=f"slow-in-flight-{index}",
            )
            for index in range(3)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound safety rate limit reached"


@pytest.mark.asyncio
async def test_stale_in_flight_duplicate_is_suppressed_beyond_duplicate_window(db_session):
    now = utcnow()
    current = _row(chat_id="222@c.us", status="pending", updated_at=now, text="same exact content")
    in_flight = _row(
        chat_id="222@c.us",
        status="sending",
        updated_at=now - timedelta(minutes=20),
        text="same exact content",
    )
    db_session.add_all([current, in_flight])
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(current, now=now)

    assert decision.allowed is False
    assert decision.reason == "recent duplicate/similar outbound content suppressed"


@pytest.mark.asyncio
async def test_contact_rate_limit_aggregates_current_chat_aliases(db_session):
    now = utcnow()
    contact = Contact(whatsapp_id="222-primary@c.us", chat_id="222-alias@c.us")
    db_session.add(contact)
    await db_session.flush()
    current = _row(chat_id="222-alias@c.us", status="pending", updated_at=now, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="222-primary@c.us", status="sent", updated_at=now, text=f"prior-{index}")
            for index in range(3)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(
        current, now=now, contact_id=int(contact.id)
    )

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound safety rate limit reached"


@pytest.mark.asyncio
async def test_contact_backlog_aggregates_current_chat_aliases(db_session):
    old = utcnow() - timedelta(minutes=5)
    contact = Contact(whatsapp_id="223-primary@c.us", chat_id="223-alias@c.us")
    db_session.add(contact)
    await db_session.flush()
    current = _row(chat_id="223-alias@c.us", status="pending", updated_at=old, text="current")
    db_session.add(current)
    db_session.add_all(
        [
            _row(chat_id="223-primary@c.us", status="pending", updated_at=old, text=f"backlog-{index}")
            for index in range(10)
        ]
    )
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(
        current, now=utcnow(), contact_id=int(contact.id)
    )

    assert decision.allowed is False
    assert decision.reason == "per-contact outbound queue backpressure limit exceeded"


@pytest.mark.asyncio
async def test_identical_blank_caption_media_is_suppressed_across_contact_aliases(db_session):
    now = utcnow()
    contact = Contact(whatsapp_id="224-primary@c.us", chat_id="224-alias@c.us")
    db_session.add(contact)
    await db_session.flush()
    media = {
        "media_url": "http://waha:3000/api/files/exact-image.jpg",
        "media_type": "image",
        "media_caption": "",
        "formatting_json": {"media_mime": "image/jpeg", "media_filename": "exact-image.jpg"},
    }
    current = _row(chat_id="224-alias@c.us", status="pending", updated_at=now, text="", **media)
    previous = _row(chat_id="224-primary@c.us", status="sent", updated_at=now, text="", **media)
    db_session.add_all([current, previous])
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(
        current, now=now, contact_id=int(contact.id)
    )

    assert decision.allowed is False
    assert decision.reason == "recent duplicate/similar outbound content suppressed"


@pytest.mark.asyncio
async def test_distinct_media_with_same_caption_is_not_a_duplicate(db_session):
    now = utcnow()
    contact = Contact(whatsapp_id="225-primary@c.us", chat_id="225-alias@c.us")
    db_session.add(contact)
    await db_session.flush()
    current = _row(
        chat_id="225-alias@c.us",
        status="pending",
        updated_at=now,
        text="",
        media_url="http://waha:3000/api/files/current.jpg",
        media_type="image",
        media_caption="Same caption",
        formatting_json={"media_mime": "image/jpeg", "media_filename": "current.jpg"},
    )
    previous = _row(
        chat_id="225-primary@c.us",
        status="sent",
        updated_at=now,
        text="",
        media_url="http://waha:3000/api/files/previous.jpg",
        media_type="image",
        media_caption="Same caption",
        formatting_json={"media_mime": "image/jpeg", "media_filename": "previous.jpg"},
    )
    db_session.add_all([current, previous])
    await db_session.flush()

    decision = await OutboundSafetyLimitService(db_session).authorize(
        current, now=now, contact_id=int(contact.id)
    )

    assert decision.allowed is True
    assert decision.reason == "outbound safety limits allow delivery"

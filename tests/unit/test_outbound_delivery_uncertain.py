from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.schema import OutboundMessage
from app.services.waha_client import WahaClientError
from app.utils.time import utcnow
from app.workers import background_workers


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ExplodingClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")


class _UncertainClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise WahaClientError("connection closed before response")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise WahaClientError("connection closed before response")


@pytest.mark.asyncio
async def test_stale_sending_row_is_quarantined_without_waha_replay(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="already attempted",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(row)
    await db_session.commit()
    row_id = row.id

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    client = _ExplodingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 0
    assert client.calls == 0
    assert row.id == row_id
    assert row.status == "deferred"
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_waha_send_error_is_delivery_uncertain_not_retrying(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="attempt once",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    client = _UncertainClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == 1
    assert row.status == "deferred"
    assert row.retry_count == 0
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_delivery_uncertain_state_survives_restart_style_reload(db_session):
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="uncertain",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(row)
    await db_session.flush()
    row_id = row.id

    await background_workers._mark_delivery_uncertain(
        db_session,
        row,
        reason="delivery outcome uncertain; automatic replay blocked",
    )
    db_session.expire_all()

    persisted = await db_session.get(OutboundMessage, row_id)
    assert persisted is not None
    assert persisted.status == "deferred"
    assert "automatic replay blocked" in (persisted.error_message or "")

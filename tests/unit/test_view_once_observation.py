"""View-once capability observation at ingress.

Observation is evidence gathering, never authority and never a reply trigger. These
tests pin that ordinary media is never promoted, that observation is idempotent per
canonical source message, that OWNER deletion survives duplicate deliveries, and that
no bytes, base64, or transport locator is ever persisted.
"""

from __future__ import annotations

import pytest
from sqlalchemy import text

from app.services.view_once_observation_service import ViewOnceObservationService


CHAT = "2348000000002@c.us"


def _payload(source_id="SRC-1", **overrides):
    payload = {"id": source_id, "chatId": CHAT, "from": CHAT, "type": "image", "hasMedia": True}
    payload.update(overrides)
    return payload


async def _observe(db_session, payload, *, source_id=None, chat_id=CHAT, contact_id=None):
    return await ViewOnceObservationService(db_session).observe(
        payload=payload,
        source_message_id=source_id if source_id is not None else payload.get("id", ""),
        source_chat_id=chat_id,
        source_contact_id=contact_id,
    )


async def _rows(db_session):
    result = await db_session.execute(
        text(
            "SELECT source_message_id, media_type, media_mime, capability_state, "
            "transport_available, retention_mode, deleted_at, metadata_json "
            "FROM view_once_media_metadata ORDER BY id"
        )
    )
    return [dict(row) for row in result.mappings().all()]


# --------------------------------------------------------------------------------------
# Ordinary media is never promoted
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize("declared_type", ["image", "video", "audio", "ptt", "document"])
async def test_ordinary_media_is_never_observed_as_view_once(db_session, declared_type):
    observation = await _observe(
        db_session,
        _payload(type=declared_type, media={"url": "http://waha:3000/api/files/a", "mimetype": "image/jpeg"}),
    )

    assert observation.recorded is False
    assert await _rows(db_session) == []


@pytest.mark.asyncio
async def test_explicit_false_marker_is_not_observed(db_session):
    observation = await _observe(db_session, _payload(isViewOnce=False, media={"url": "http://x/a.jpg"}))

    assert observation.recorded is False
    assert await _rows(db_session) == []


@pytest.mark.asyncio
async def test_conflicting_markers_fail_closed(db_session):
    """An explicit negative must dominate a positive rather than being ignored."""
    observation = await _observe(
        db_session,
        _payload(isViewOnce=True, message={"viewOnce": False}, media={"url": "http://x/a.jpg"}),
    )

    assert observation.recorded is False
    assert await _rows(db_session) == []


# --------------------------------------------------------------------------------------
# Explicit evidence is observed
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_view_once_with_locator_is_transient_available(db_session):
    observation = await _observe(
        db_session,
        _payload(isViewOnce=True, media={"url": "http://waha:3000/api/files/a.jpg", "mimetype": "image/jpeg", "type": "image"}),
    )

    assert observation.recorded is True
    assert observation.capability_state == ViewOnceObservationService.STATE_TRANSIENT_AVAILABLE

    rows = await _rows(db_session)
    assert len(rows) == 1
    assert rows[0]["source_message_id"] == "SRC-1"
    assert rows[0]["transport_available"] is True
    assert rows[0]["retention_mode"] == "none"


@pytest.mark.asyncio
async def test_explicit_view_once_without_locator_is_capability_verified(db_session):
    observation = await _observe(db_session, _payload(isViewOnce=True, hasMedia=True))

    assert observation.recorded is True
    assert observation.capability_state == ViewOnceObservationService.STATE_CAPABILITY_VERIFIED

    rows = await _rows(db_session)
    assert rows[0]["transport_available"] is False


@pytest.mark.asyncio
async def test_engine_wrapper_evidence_is_observed(db_session):
    observation = await _observe(
        db_session,
        _payload(message={"viewOnceMessageV2": {"message": {"imageMessage": {}}}}, media={"url": "http://x/a.jpg"}),
    )

    assert observation.recorded is True


# --------------------------------------------------------------------------------------
# Canonical source identity
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_evidence_disagreeing_with_canonical_source_fails_closed(db_session):
    """Detector evidence describing a different message must not be attached."""
    observation = await _observe(
        db_session,
        _payload(source_id="OUTER-1", isViewOnce=True, media={"url": "http://x/a.jpg"}),
        source_id="DIFFERENT-CANONICAL-ID",
    )

    assert observation.recorded is False
    assert await _rows(db_session) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_id", ["", "   ", "x" * 250])
async def test_missing_or_oversized_canonical_source_is_rejected(db_session, bad_id):
    observation = await _observe(
        db_session, _payload(isViewOnce=True, media={"url": "http://x/a.jpg"}), source_id=bad_id
    )

    assert observation.recorded is False
    assert await _rows(db_session) == []


# --------------------------------------------------------------------------------------
# Idempotency and durability
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_delivery_of_one_source_creates_one_row(db_session):
    """`message` and `message.any` plus webhook retries must converge on one record."""
    payload = _payload(isViewOnce=True, media={"url": "http://x/a.jpg", "mimetype": "image/jpeg"})

    for _ in range(4):
        await _observe(db_session, payload)

    assert len(await _rows(db_session)) == 1


@pytest.mark.asyncio
async def test_distinct_sources_create_distinct_rows(db_session):
    for source_id in ("SRC-A", "SRC-B"):
        await _observe(db_session, _payload(source_id=source_id, isViewOnce=True, media={"url": "http://x/a.jpg"}))

    assert len(await _rows(db_session)) == 2


@pytest.mark.asyncio
async def test_deleted_record_is_not_resurrected_by_duplicate_delivery(db_session):
    """OWNER deletion must stay durable across replays and restarts."""
    payload = _payload(isViewOnce=True, media={"url": "http://x/a.jpg"})
    await _observe(db_session, payload)
    await db_session.execute(
        text("UPDATE view_once_media_metadata SET deleted_at = now() WHERE source_message_id = 'SRC-1'")
    )

    await _observe(db_session, payload)

    rows = await _rows(db_session)
    assert len(rows) == 1
    assert rows[0]["deleted_at"] is not None


@pytest.mark.asyncio
async def test_capability_state_is_refreshed_on_reobservation(db_session):
    await _observe(db_session, _payload(isViewOnce=True, hasMedia=True))
    assert (await _rows(db_session))[0]["transport_available"] is False

    await _observe(db_session, _payload(isViewOnce=True, media={"url": "http://x/a.jpg"}))

    rows = await _rows(db_session)
    assert len(rows) == 1
    assert rows[0]["transport_available"] is True


# --------------------------------------------------------------------------------------
# Privacy: no bytes, no base64, no transport locator
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_transport_locator_or_bytes_are_persisted(db_session):
    secret_url = "http://waha:3000/api/files/SECRET-CAPABILITY-TOKEN.jpg"
    await _observe(
        db_session,
        _payload(
            isViewOnce=True,
            media={"url": secret_url, "mimetype": "image/jpeg", "data": "BASE64BYTESHERE"},
        ),
    )

    persisted = str(await _rows(db_session))
    assert "SECRET-CAPABILITY-TOKEN" not in persisted
    assert "BASE64BYTESHERE" not in persisted
    assert "api/files" not in persisted


@pytest.mark.asyncio
async def test_observation_failure_never_raises_into_ingress(db_session, monkeypatch):
    """A capability record must never be able to break message persistence."""

    async def _boom(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(ViewOnceObservationService, "_upsert", _boom)

    observation = await _observe(db_session, _payload(isViewOnce=True, media={"url": "http://x/a.jpg"}))

    assert observation.recorded is False
    assert "could not be persisted" in observation.reason

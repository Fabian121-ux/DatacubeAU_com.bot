from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.services.view_once_command_service import ViewOnceCommandService
from app.services.view_once_media_service import ViewOnceMediaService
from app.utils.time import utcnow


OWNER_CHAT = "2348000000001@c.us"
PEER_CHAT = "2348000000002@c.us"
PRIVATE_MEDIA_URL = "http://waha:3000/api/files/private-token"


def _message(*, source_id: str = "VV-TIME-1", timestamp=1700000000) -> SimpleNamespace:
    return SimpleNamespace(
        chat_id=PEER_CHAT,
        payload={
            "id": "OWNER-CMD-TIME-1",
            "chatId": PEER_CHAT,
            "fromMe": True,
            "body": ".vv info",
            "replyTo": {
                "id": source_id,
                "timestamp": timestamp,
                "viewOnce": True,
                "media": {
                    "url": PRIVATE_MEDIA_URL,
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            },
        },
    )


@pytest.mark.asyncio
async def test_safe_original_timestamp_and_capability_expiry_are_persisted_without_media_url(db_session):
    media = ViewOnceMediaService(db_session)
    message = _message()

    _, record = await media.observe_reply(message)
    assert record is not None
    assert record.original_message_at == "2023-11-14T22:13:20+00:00"
    assert record.capability_expires_at is None

    expires_at = utcnow() + timedelta(minutes=15)
    await media.mark_capability_expiry(record.source_message_id, expires_at)

    refreshed = await media.get(record.source_message_id)
    assert refreshed is not None
    assert refreshed.capability_expires_at == expires_at.isoformat()

    raw = (
        await db_session.execute(
            text(
                "SELECT metadata_json::text AS metadata "
                "FROM view_once_media_metadata WHERE source_message_id = 'VV-TIME-1'"
            )
        )
    ).mappings().one()["metadata"]
    assert "2023-11-14T22:13:20+00:00" in raw
    assert expires_at.isoformat() in raw
    assert "private-token" not in raw


@pytest.mark.asyncio
async def test_reobserving_for_info_preserves_existing_capability_expiry_and_renders_safe_contract(db_session):
    media = ViewOnceMediaService(db_session)
    message = _message(source_id="VV-TIME-INFO")
    _, record = await media.observe_reply(message)
    assert record is not None

    expires_at = utcnow() + timedelta(minutes=15)
    await media.mark_capability_expiry(record.source_message_id, expires_at)

    service = ViewOnceCommandService(db_session)
    result = await service._info(message, OWNER_CHAT, "req-time", "transport-time")

    assert result.reply_text is not None
    assert "Original sent: 2023-11-14T22:13:20+00:00" in result.reply_text
    assert f"Temporary capability expiry: {expires_at.isoformat()}" in result.reply_text
    assert "Retention: none" in result.reply_text
    assert "Retained at: not retained" in result.reply_text
    assert "Retention expiry: not applicable" in result.reply_text
    assert PRIVATE_MEDIA_URL not in result.reply_text

    refreshed = await media.get(record.source_message_id)
    assert refreshed is not None
    assert refreshed.capability_expires_at == expires_at.isoformat()


@pytest.mark.asyncio
async def test_conflicting_supported_reply_timestamps_fail_to_unknown_instead_of_guessing(db_session):
    media = ViewOnceMediaService(db_session)
    message = _message(source_id="VV-TIME-CONFLICT", timestamp=1700000000)
    message.payload["replyTo"]["_data"] = {
        "id": "VV-TIME-CONFLICT",
        "timestamp": 1700000300,
        "viewOnce": True,
        "media": {"mimetype": "image/jpeg", "type": "image"},
    }

    _, record = await media.observe_reply(message)

    assert record is not None
    assert record.original_message_at is None

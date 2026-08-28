from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.config import settings
from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.services.view_once_media_service import ViewOnceMediaService


def _reply(source_id: str, *, timestamp=None, media: dict | None = None) -> SimpleNamespace:
    reply_to = {
        "id": source_id,
        "viewOnce": True,
        "media": media
        or {
            "url": settings.waha_service_url.rstrip("/") + f"/api/files/{source_id}.jpg",
            "type": "image",
            "mimetype": "image/jpeg",
        },
    }
    if timestamp is not None:
        reply_to["timestamp"] = timestamp
    return SimpleNamespace(chat_id="2348000000002@c.us", payload={"replyTo": reply_to})


@pytest.mark.asyncio
async def test_sparse_reobservation_preserves_known_original_timestamp(db_session):
    media = ViewOnceMediaService(db_session)
    source_id = "TIMESTAMP-PRESERVE"

    _, first = await media.observe_reply(_reply(source_id, timestamp=1_725_000_000))
    assert first is not None
    assert first.original_message_at is not None
    original = first.original_message_at

    _, second = await media.observe_reply(_reply(source_id))
    assert second is not None
    assert second.original_message_at == original

    persisted = await media.get(source_id)
    assert persisted is not None
    assert persisted.original_message_at == original


def test_reply_media_size_checks_all_aliases_and_uses_largest_valid_value():
    payload = {
        "replyTo": {
            "id": "SIZE-ALIASES",
            "viewOnce": True,
            "media": {
                "url": settings.waha_service_url.rstrip("/") + "/api/files/size-aliases.jpg",
                "type": "image",
                "mimetype": "image/jpeg",
                "fileSize": 1,
                "filesize": "not-a-number",
                "size": 60_000_000,
            },
        }
    }

    assert ViewOnceCapabilityService.reply_media_size(payload) == 60_000_000

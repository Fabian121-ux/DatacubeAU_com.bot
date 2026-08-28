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


def test_overlong_snapshot_id_is_conflicting_not_missing():
    valid_nested_id = "NESTED-SOURCE"
    payload = {
        "replyTo": {
            "id": "A" * 201,
            "media": {
                "url": settings.waha_service_url.rstrip("/") + "/api/files/root.jpg",
                "type": "image",
                "mimetype": "image/jpeg",
            },
            "message": {
                "id": valid_nested_id,
                "viewOnce": True,
                "media": {
                    "url": settings.waha_service_url.rstrip("/") + "/api/files/nested.jpg",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            },
        }
    }

    capability = ViewOnceCapabilityService.inspect_reply_snapshot(payload)

    assert capability.source_message_id is None
    assert capability.is_view_once is None
    assert capability.media_url is None
    assert "disagree" in capability.reason.lower()


@pytest.mark.asyncio
async def test_sparse_reobservation_preserves_known_media_type_and_mime(db_session):
    media_service = ViewOnceMediaService(db_session)
    source_id = "MEDIA-METADATA-PRESERVE"

    _, first = await media_service.observe_reply(_reply(source_id))
    assert first is not None
    assert first.media_type == "image"
    assert first.media_mime == "image/jpeg"

    sparse_media = {
        "url": settings.waha_service_url.rstrip("/") + f"/api/files/{source_id}.jpg",
    }
    _, second = await media_service.observe_reply(_reply(source_id, media=sparse_media))

    assert second is not None
    assert second.media_type == "image"
    assert second.media_mime == "image/jpeg"

    persisted = await media_service.get(source_id)
    assert persisted is not None
    assert persisted.media_type == "image"
    assert persisted.media_mime == "image/jpeg"


@pytest.mark.asyncio
async def test_reobservation_preserves_deleted_tombstone_and_list_exclusion(db_session):
    media_service = ViewOnceMediaService(db_session)
    source_id = "DELETED-TOMBSTONE-PRESERVE"

    _, observed = await media_service.observe_reply(_reply(source_id))
    assert observed is not None
    assert observed.deleted_at is None

    deleted = await media_service.delete(source_id)
    assert deleted is not None
    assert deleted.deleted_at is not None
    assert deleted.capability_state == "deleted"
    deleted_at = deleted.deleted_at

    _, reobserved = await media_service.observe_reply(_reply(source_id))
    assert reobserved is not None
    assert reobserved.deleted_at == deleted_at
    assert reobserved.capability_state == "deleted"
    assert reobserved.transport_available is False

    persisted = await media_service.get(source_id)
    assert persisted is not None
    assert persisted.deleted_at == deleted_at
    assert persisted.capability_state == "deleted"

    recent = await media_service.list_recent(ViewOnceMediaService.MAX_LIST_LIMIT)
    assert source_id not in {record.source_message_id for record in recent}

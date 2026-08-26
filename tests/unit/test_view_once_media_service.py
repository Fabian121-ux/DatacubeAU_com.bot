from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.services.view_once_media_service import ViewOnceMediaService


OWNER_CHAT = "2348000000001@c.us"
PEER_CHAT = "2348000000002@c.us"


def _message(reply_to: dict) -> SimpleNamespace:
    return SimpleNamespace(
        chat_id=PEER_CHAT,
        payload={
            "id": "OWNER-CMD-1",
            "chatId": PEER_CHAT,
            "fromMe": True,
            "body": ".vv",
            "replyTo": reply_to,
        },
    )


@pytest.mark.asyncio
async def test_observe_reply_persists_metadata_without_private_media_url(db_session):
    service = ViewOnceMediaService(db_session)
    message = _message(
        {
            "id": "VV-1",
            "viewOnce": True,
            "media": {"url": "http://waha:3000/api/files/private-token", "mimetype": "image/jpeg", "type": "image"},
        }
    )

    capability, record = await service.observe_reply(message)

    assert capability.retrievable_now is True
    assert record is not None
    assert record.capability_state == "available_from_transport"
    row = (
        await db_session.execute(
            text("SELECT metadata_json::text AS metadata, retention_mode FROM view_once_media_metadata WHERE source_message_id='VV-1'")
        )
    ).mappings().one()
    assert "private-token" not in row["metadata"]
    assert row["retention_mode"] == "none"


@pytest.mark.asyncio
async def test_plain_media_is_recorded_as_capability_unknown_not_view_once(db_session):
    service = ViewOnceMediaService(db_session)
    capability, record = await service.observe_reply(
        _message({"id": "VV-2", "hasMedia": True, "media": {"url": "http://waha:3000/file", "type": "image"}})
    )

    assert capability.is_view_once is None
    assert capability.retrievable_now is False
    assert record is not None
    assert record.capability_state == "capability_unknown"
    assert record.transport_available is False


@pytest.mark.asyncio
async def test_explicit_view_once_without_media_is_truthfully_unavailable(db_session):
    service = ViewOnceMediaService(db_session)
    capability, record = await service.observe_reply(_message({"id": "VV-3", "viewOnce": True, "hasMedia": True}))

    assert capability.is_view_once is True
    assert capability.retrievable_now is False
    assert record is not None
    assert record.capability_state == "unavailable"


@pytest.mark.asyncio
async def test_recent_list_is_bounded_and_delete_targets_only_selected_record(db_session):
    service = ViewOnceMediaService(db_session)
    await service.observe_reply(_message({"id": "VV-A", "viewOnce": True, "media": {"url": "http://waha/a", "type": "image"}}))
    await service.observe_reply(_message({"id": "VV-B", "viewOnce": True, "media": {"url": "http://waha/b", "type": "video"}}))

    rows = await service.list_recent(999)
    assert len(rows) == 2
    assert service.MAX_LIST_LIMIT == 25

    assert await service.delete_metadata("VV-A") is True
    assert await service.delete_metadata("VV-A") is False
    assert (await service.get("VV-A")).deleted_at is not None
    assert (await service.get("VV-B")).deleted_at is None


@pytest.mark.asyncio
async def test_mark_returned_records_lifecycle_without_retaining_media(db_session):
    service = ViewOnceMediaService(db_session)
    await service.observe_reply(
        _message({"id": "VV-RETURN", "viewOnce": True, "media": {"url": "http://waha/private", "type": "image"}})
    )

    await service.mark_returned("VV-RETURN")
    record = await service.get("VV-RETURN")

    assert record is not None
    assert record.returned_to_owner_at is not None
    assert record.retention_mode == "none"
    assert service.retention_supported() is False

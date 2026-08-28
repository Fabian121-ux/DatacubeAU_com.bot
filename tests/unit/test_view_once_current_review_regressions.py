from __future__ import annotations

from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.config import settings
from app.models.schema import OutboundMessage
from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.services.view_once_command_service import ViewOnceCommandService
from app.services.view_once_media_service import ViewOnceMediaService
from app.utils.time import utcnow


OWNER_ID = "2348000000001@c.us"


def _owner() -> SimpleNamespace:
    return SimpleNamespace(
        normalized_whatsapp_id=OWNER_ID,
        whatsapp_number="2348000000001",
        permission_level="owner",
    )


def test_deep_same_message_media_size_is_included_in_safety_ceiling():
    payload = {
        "replyTo": {
            "id": "DEEP-SIZE",
            "viewOnce": True,
            "media": {
                "url": settings.waha_service_url.rstrip("/") + "/api/files/deep-size.jpg",
                "type": "image",
                "mimetype": "image/jpeg",
            },
            "message": {
                "id": "DEEP-SIZE",
                "_data": {
                    "id": "DEEP-SIZE",
                    "media": {"fileSize": ViewOnceCommandService.MAX_MEDIA_BYTES + 1},
                },
            },
        }
    }

    assert ViewOnceCapabilityService.reply_media_size(payload) == ViewOnceCommandService.MAX_MEDIA_BYTES + 1


@pytest.mark.asyncio
async def test_deep_oversized_snapshot_never_queues_private_media(db_session):
    service = ViewOnceCommandService(db_session)
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": "DEEP-SIZE-CMD",
                "viewOnce": True,
                "media": {
                    "url": settings.waha_service_url.rstrip("/") + "/api/files/deep-size-command.jpg",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
                "message": {
                    "id": "DEEP-SIZE-CMD",
                    "_data": {
                        "id": "DEEP-SIZE-CMD",
                        "media": {"size": ViewOnceCommandService.MAX_MEDIA_BYTES + 1},
                    },
                },
            }
        },
    )

    result = await service.handle(
        ".vv",
        "",
        message=message,
        owner=_owner(),
        permission="owner",
        request_id="DEEP-SIZE-CMD",
        transport_message_id="DEEP-SIZE-CMD",
    )

    assert result.error == "media too large"
    queued = (
        await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id))
    ).scalar_one()
    assert queued.media_url is None
    assert "50 mb" in queued.message_text.lower()


@pytest.mark.asyncio
async def test_overlong_delete_id_cannot_delete_matching_200_char_source(db_session):
    source_id = "S" * ViewOnceMediaService.MAX_SOURCE_MESSAGE_ID_CHARS
    media = ViewOnceMediaService(db_session)
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": source_id,
                "viewOnce": True,
                "media": {
                    "url": settings.waha_service_url.rstrip("/") + "/api/files/exact-id.jpg",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            }
        },
    )
    _, observed = await media.observe_reply(message)
    assert observed is not None

    service = ViewOnceCommandService(db_session)
    result = await service.handle(
        ".vv",
        "delete " + source_id + "X",
        message=SimpleNamespace(payload={}),
        owner=_owner(),
        permission="owner",
        request_id="VV-OVERLONG-DELETE",
        transport_message_id="VV-OVERLONG-DELETE",
    )

    assert result.error == "invalid source message id"
    still_present = await media.get(source_id)
    assert still_present is not None
    assert still_present.deleted_at is None


def test_malformed_absolute_media_url_is_untrusted_instead_of_raising():
    assert ViewOnceCommandService._trusted_waha_media_url("http://[bad/api/files/item") is False


@pytest.mark.asyncio
async def test_malformed_media_url_returns_private_rejection_without_media_queue(db_session):
    service = ViewOnceCommandService(db_session)
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": "MALFORMED-URL",
                "viewOnce": True,
                "media": {
                    "url": "http://[bad/api/files/item",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            }
        },
    )

    result = await service.handle(
        ".vv",
        "",
        message=message,
        owner=_owner(),
        permission="owner",
        request_id="MALFORMED-URL",
        transport_message_id="MALFORMED-URL",
    )

    assert result.error == "untrusted media url"
    queued = (
        await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id))
    ).scalar_one()
    assert queued.media_url is None
    assert "blocked" in queued.message_text.lower()


def test_waha_file_capability_rejects_path_escape_and_encoded_separators():
    origin = settings.waha_service_url.rstrip("/")
    assert ViewOnceCommandService._trusted_waha_media_url(origin + "/api/files/photo.jpg") is True
    assert ViewOnceCommandService._trusted_waha_media_url(origin + "/api/files/../../api/sessions") is False
    assert ViewOnceCommandService._trusted_waha_media_url(origin + "/api/files/%2e%2e/%2e%2e/api/sessions") is False
    assert ViewOnceCommandService._trusted_waha_media_url(origin + "/api/files/item%2f..%2f..%2fapi%2fsessions") is False
    assert ViewOnceCommandService._trusted_waha_media_url(origin + "/api/files/item%5c..%5capi%5csessions") is False


@pytest.mark.asyncio
async def test_path_escape_media_url_returns_private_rejection_without_media_queue(db_session):
    service = ViewOnceCommandService(db_session)
    origin = settings.waha_service_url.rstrip("/")
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": "PATH-ESCAPE-URL",
                "viewOnce": True,
                "media": {
                    "url": origin + "/api/files/../../api/sessions",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            }
        },
    )

    result = await service.handle(
        ".vv",
        "",
        message=message,
        owner=_owner(),
        permission="owner",
        request_id="PATH-ESCAPE-URL",
        transport_message_id="PATH-ESCAPE-URL",
    )

    assert result.error == "untrusted media url"
    queued = (
        await db_session.execute(select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id))
    ).scalar_one()
    assert queued.media_url is None
    assert "blocked" in queued.message_text.lower()


@pytest.mark.asyncio
async def test_capability_expiry_jsonb_bind_is_typed_and_round_trips(db_session):
    media = ViewOnceMediaService(db_session)
    source_id = "EXPIRY-BIND"
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": source_id,
                "viewOnce": True,
                "media": {
                    "url": settings.waha_service_url.rstrip("/") + "/api/files/expiry-bind.jpg",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            }
        },
    )
    _, observed = await media.observe_reply(message)
    assert observed is not None

    expires_at = utcnow() + timedelta(minutes=15)
    await media.mark_capability_expiry(source_id, expires_at)
    record = await media.get(source_id)

    assert record is not None
    assert record.capability_expires_at == expires_at.isoformat()

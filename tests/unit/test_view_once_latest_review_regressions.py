from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.models.schema import OutboundMessage
from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.services.view_once_command_service import ViewOnceCommandService
from app.utils.time import utcnow


OWNER_ID = "2348000000001@c.us"


def test_root_negative_marker_wins_over_unrelated_nested_context_view_once_marker():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "ROOT-MSG",
                "viewOnce": False,
                "media": {
                    "url": "http://waha:3000/api/files/ordinary.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
                "contextInfo": {"quotedMessage": {"viewOnce": True}},
            }
        }
    )

    assert capability.source_message_id == "ROOT-MSG"
    assert capability.is_view_once is False
    assert capability.retrievable_now is False


def test_root_negative_marker_wins_even_when_wrapper_key_appears_first():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "ROOT-ORDER-MSG",
                "viewOnceMessage": {"message": {"imageMessage": {}}},
                "viewOnce": False,
                "media": {
                    "url": "http://waha:3000/api/files/ordinary-order.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            }
        }
    )

    assert capability.source_message_id == "ROOT-ORDER-MSG"
    assert capability.is_view_once is False
    assert capability.retrievable_now is False


def test_unrelated_nested_context_marker_is_not_treated_as_source_view_once_evidence():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "ROOT-MSG-2",
                "media": {
                    "url": "http://waha:3000/api/files/ordinary-2.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
                "contextInfo": {"quotedMessage": {"viewOnce": True}},
            }
        }
    )

    assert capability.source_message_id == "ROOT-MSG-2"
    assert capability.is_view_once is None
    assert capability.retrievable_now is False


def test_reply_snapshot_resolves_source_id_from_supported_nested_message_shape():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "message": {
                    "id": {"_serialized": "NESTED-SOURCE-ID"},
                    "viewOnce": True,
                    "media": {
                        "url": "http://waha:3000/api/files/nested.jpg",
                        "mimetype": "image/jpeg",
                        "type": "image",
                    },
                }
            }
        }
    )

    assert capability.source_message_id == "NESTED-SOURCE-ID"
    assert capability.is_view_once is True
    assert capability.retrievable_now is True


def test_reply_snapshot_resolves_source_id_from_supported_data_shape():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "_data": {
                    "id": "DATA-SOURCE-ID",
                    "viewOnce": True,
                    "media": {
                        "url": "http://waha:3000/api/files/data.jpg",
                        "mimetype": "image/jpeg",
                        "type": "image",
                    },
                }
            }
        }
    )

    assert capability.source_message_id == "DATA-SOURCE-ID"
    assert capability.is_view_once is True
    assert capability.retrievable_now is True


@pytest.mark.asyncio
async def test_unsupported_vv_subcommand_queues_help_to_owner_self_dm(db_session):
    service = ViewOnceCommandService(db_session)

    result = await service.handle(
        ".vv",
        "foo",
        message=SimpleNamespace(payload={}),
        owner=SimpleNamespace(normalized_whatsapp_id=OWNER_ID, whatsapp_number="2348000000001"),
        permission="owner",
        request_id="VV-UNSUPPORTED",
        transport_message_id="VV-UNSUPPORTED",
    )

    assert result.consumed is True
    assert result.error == "unsupported view-once subcommand"
    assert result.outbound_queue_id is not None

    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id)
        )
    ).scalar_one()
    assert queued.chat_id == OWNER_ID
    assert queued.media_url is None
    assert "view-once commands" in queued.message_text.lower()


@pytest.mark.asyncio
async def test_conflicting_image_type_and_video_mime_never_queues_media(db_session):
    service = ViewOnceCommandService(db_session)
    message = SimpleNamespace(
        payload={
            "replyTo": {
                "id": "VV-CONFLICT",
                "viewOnce": True,
                "media": {
                    "url": "http://waha:3000/api/files/conflict.mp4",
                    "type": "image",
                    "mimetype": "video/mp4",
                },
            }
        }
    )

    result = await service.handle(
        ".vv",
        "",
        message=message,
        owner=SimpleNamespace(normalized_whatsapp_id=OWNER_ID, whatsapp_number="2348000000001"),
        permission="owner",
        request_id="VV-CONFLICT",
        transport_message_id="VV-CONFLICT",
    )

    assert result.consumed is True
    assert result.error == "unsupported media type"
    assert result.outbound_queue_id is not None

    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id)
        )
    ).scalar_one()
    assert queued.chat_id == OWNER_ID
    assert queued.media_url is None
    assert "unsupported" in queued.message_text.lower()


@pytest.mark.asyncio
async def test_vv_media_queue_has_absolute_capability_expiry(db_session):
    service = ViewOnceCommandService(db_session)
    message = SimpleNamespace(
        chat_id="2348000000002@c.us",
        payload={
            "replyTo": {
                "id": "VV-EXPIRY",
                "viewOnce": True,
                "media": {
                    "url": "http://waha:3000/api/files/expiry.jpg",
                    "type": "image",
                    "mimetype": "image/jpeg",
                },
            }
        },
    )

    before = utcnow()
    result = await service.handle(
        ".vv",
        "",
        message=message,
        owner=SimpleNamespace(normalized_whatsapp_id=OWNER_ID, whatsapp_number="2348000000001"),
        permission="owner",
        request_id="VV-EXPIRY",
        transport_message_id="VV-EXPIRY",
    )

    queued = (
        await db_session.execute(
            select(OutboundMessage).where(OutboundMessage.id == result.outbound_queue_id)
        )
    ).scalar_one()
    expires_at = datetime.fromisoformat(queued.formatting_json["capability_expires_at"])
    assert expires_at > before
    assert expires_at <= before + ViewOnceCommandService.DELIVERY_CAPABILITY_TTL
    assert queued.media_url == "http://waha:3000/api/files/expiry.jpg"

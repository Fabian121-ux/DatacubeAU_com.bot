from __future__ import annotations

from app.services.view_once_capability_service import ViewOnceCapabilityService
from app.services.view_once_command_service import ViewOnceCommandService


def test_non_image_mime_in_later_same_id_snapshot_fails_closed() -> None:
    payload = {
        "replyTo": {
            "id": "SOURCE-1",
            "viewOnce": True,
            "media": {
                "url": "http://waha:3000/api/files/photo.jpg",
                "type": "image",
                "mimetype": "image/jpeg",
            },
            "_data": {
                "id": "SOURCE-1",
                "media": {
                    "mimetype": "application/pdf",
                },
            },
        }
    }

    capability = ViewOnceCapabilityService.inspect_reply_snapshot(payload)

    assert capability.source_message_id == "SOURCE-1"
    assert capability.is_view_once is True
    assert capability.media_url == "http://waha:3000/api/files/photo.jpg"
    assert capability.media_mime is None
    assert capability.media_type is None
    assert ViewOnceCommandService._safe_media_type(capability.media_type, capability.media_mime) is None


def test_supported_image_mime_across_same_id_snapshots_remains_usable() -> None:
    payload = {
        "replyTo": {
            "id": "SOURCE-2",
            "viewOnce": True,
            "media": {"url": "http://waha:3000/api/files/photo.jpg"},
            "message": {
                "id": "SOURCE-2",
                "media": {"type": "image", "mimetype": "image/jpeg"},
            },
        }
    }

    capability = ViewOnceCapabilityService.inspect_reply_snapshot(payload)

    assert capability.media_mime == "image/jpeg"
    assert capability.media_type == "image"
    assert ViewOnceCommandService._safe_media_type(capability.media_type, capability.media_mime) == "image"

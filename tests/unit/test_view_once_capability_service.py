from app.services.view_once_capability_service import ViewOnceCapabilityService


def test_plain_media_is_not_inferred_as_view_once():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "ABC123",
                "hasMedia": True,
                "media": {
                    "url": "http://waha:3000/api/files/example.jpg",
                    "mimetype": "image/jpeg",
                },
            }
        }
    )

    assert capability.source_message_id == "ABC123"
    assert capability.is_view_once is None
    assert capability.retrievable_now is False
    assert "no explicit view-once evidence" in capability.reason.lower()


def test_explicit_view_once_with_media_is_retrievable_now():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": {"_serialized": "MSG-1"},
                "viewOnce": True,
                "media": {
                    "url": "http://waha:3000/api/files/view-once.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            }
        }
    )

    assert capability.source_message_id == "MSG-1"
    assert capability.is_view_once is True
    assert capability.media_mime == "image/jpeg"
    assert capability.media_type == "image"
    assert capability.retrievable_now is True


def test_explicit_view_once_without_media_reports_unavailable():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {"replyTo": {"id": "MSG-2", "isViewOnce": True, "hasMedia": True}}
    )

    assert capability.is_view_once is True
    assert capability.media_url is None
    assert capability.retrievable_now is False
    assert "no longer retrievable" in capability.reason.lower()


def test_explicit_false_marker_denies_view_once_classification():
    capability = ViewOnceCapabilityService.inspect_message_payload(
        {
            "id": "MSG-3",
            "view_once": False,
            "media": {"url": "http://waha:3000/api/files/normal.jpg"},
        }
    )

    assert capability.is_view_once is False
    assert capability.retrievable_now is False
    assert "not view-once" in capability.reason.lower()


def test_engine_wrapper_counts_as_explicit_view_once_evidence():
    capability = ViewOnceCapabilityService.inspect_message_payload(
        {
            "id": "MSG-4",
            "message": {
                "viewOnceMessageV2": {
                    "message": {
                        "imageMessage": {"caption": "private"},
                    }
                }
            },
            "media": {
                "url": "http://waha:3000/api/files/wrapped.jpg",
                "mimetype": "image/jpeg",
            },
        }
    )

    assert capability.is_view_once is True
    assert capability.retrievable_now is True


def test_invalid_or_missing_reply_snapshot_never_claims_recovery():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot({"body": ".vv"})

    assert capability.source_message_id is None
    assert capability.is_view_once is None
    assert capability.media_url is None
    assert capability.retrievable_now is False
    assert "reply to a source message" in capability.reason.lower()

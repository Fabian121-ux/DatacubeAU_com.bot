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
                    "message": {"imageMessage": {"caption": "private"}}
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


def test_media_extractor_prefers_later_retrievable_candidate_over_metadata_only_direct_media():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "MSG-FALLBACK",
                "viewOnce": True,
                "media": {"mimetype": "image/jpeg", "type": "image"},
                "_data": {
                    "media": {
                        "url": "http://waha:3000/api/files/fallback.jpg",
                        "mimetype": "image/jpeg",
                        "type": "image",
                    }
                },
            }
        }
    )

    assert capability.media_url == "http://waha:3000/api/files/fallback.jpg"
    assert capability.retrievable_now is True


def test_media_extractor_merges_later_metadata_into_earlier_url_candidate():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "MSG-SPLIT",
                "viewOnce": True,
                "media": {"url": "http://waha:3000/api/files/split.jpg"},
                "_data": {"media": {"mimetype": "image/jpeg", "type": "image"}},
            }
        }
    )

    assert capability.media_url == "http://waha:3000/api/files/split.jpg"
    assert capability.media_mime == "image/jpeg"
    assert capability.media_type == "image"
    assert capability.retrievable_now is True


def test_conflicting_media_type_and_mime_evidence_is_discarded_fail_closed():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "MSG-CONFLICT",
                "viewOnce": True,
                "media": {
                    "url": "http://waha:3000/api/files/conflict.bin",
                    "type": "image",
                    "mimetype": "video/mp4",
                },
            }
        }
    )

    assert capability.media_url == "http://waha:3000/api/files/conflict.bin"
    assert capability.media_type is None
    assert capability.media_mime is None
    assert capability.retrievable_now is True


def test_reply_media_size_checks_all_supported_media_locations_and_uses_largest_reported_size():
    payload = {
        "replyTo": {
            "media": {"fileSize": 100},
            "message": {"media": {"filesize": 200}},
            "_data": {"media": {"size": 300}},
        }
    }

    assert ViewOnceCapabilityService.reply_media_size(payload) == 300


def test_conflicting_same_message_snapshots_fail_closed_regardless_of_container_order():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "MSG-NESTED-CONFLICT",
                "message": {"viewOnce": True},
                "_data": {"viewOnce": False},
                "media": {
                    "url": "http://waha:3000/api/files/conflict.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            }
        }
    )

    assert capability.is_view_once is False
    assert capability.retrievable_now is False


def test_numeric_zero_negative_marker_wins_over_positive_same_message_evidence():
    capability = ViewOnceCapabilityService.inspect_reply_snapshot(
        {
            "replyTo": {
                "id": "MSG-NUMERIC-ZERO",
                "viewOnce": 0,
                "_data": {"viewOnce": 1},
                "media": {
                    "url": "http://waha:3000/api/files/numeric-zero.jpg",
                    "mimetype": "image/jpeg",
                    "type": "image",
                },
            }
        }
    )

    assert capability.is_view_once is False
    assert capability.retrievable_now is False

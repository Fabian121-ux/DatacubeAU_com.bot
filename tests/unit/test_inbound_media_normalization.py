"""Canonical inbound media metadata normalization.

Field names follow the active WAHA contract taken from the bundled DTOs in the running
image, not from guesses:

- `WAMessageBase`: id, timestamp, from, fromMe, source, to, participant
- `WAMessage`:     body, hasMedia, media?, mediaUrl, ack, author?, replyTo?, _data?
- `WAMedia`:       url?, mimetype?, filename?, s3?, error?   (no size field)
- `ReplyToMessage`: id (required), participant?, body?, hasMedia, media?, _data?

Because `WAMedia` has no size field, `reported_size` is best-effort from
engine-specific `_data` and is frequently absent.

This layer is metadata only. It never classifies view-once and never stores bytes.
"""

from __future__ import annotations

import pytest

from app.core.message_normalizer import MessageNormalizer


def _normalize(payload):
    return MessageNormalizer().normalize({"event": "message", "session": "test", "payload": payload})


def _base(**overrides):
    payload = {"id": "SRC-1", "chatId": "2348000000002@c.us", "from": "2348000000002@c.us"}
    payload.update(overrides)
    return payload


# --------------------------------------------------------------------------------------
# Text remains unchanged
# --------------------------------------------------------------------------------------


def test_plain_text_message_reports_no_media():
    message = _normalize(_base(type="chat", body="hello"))

    assert message.message_text == "hello"
    assert message.media.has_media is False
    assert message.media.media_kind is None
    assert message.media.mime_type is None
    assert message.media.transient_media_available is False


# --------------------------------------------------------------------------------------
# Media kinds
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("declared_type", "mimetype", "expected_kind"),
    [
        ("image", "image/jpeg", "image"),
        ("video", "video/mp4", "video"),
        ("audio", "audio/mpeg", "audio"),
        ("ptt", "audio/ogg", "voice"),
        ("voice", "audio/ogg", "voice"),
        ("document", "application/pdf", "document"),
        ("sticker", "image/webp", "sticker"),
    ],
)
def test_media_kind_is_normalized_from_declared_type(declared_type, mimetype, expected_kind):
    message = _normalize(
        _base(type=declared_type, hasMedia=True, media={"mimetype": mimetype, "url": "http://waha:3000/api/files/a"})
    )

    assert message.media.has_media is True
    assert message.media.media_kind == expected_kind
    assert message.media.mime_type == mimetype
    assert message.media.transient_media_available is True


def test_media_kind_falls_back_to_mime_family_when_type_is_generic():
    message = _normalize(_base(type="chat", hasMedia=True, media={"mimetype": "image/png"}))

    assert message.media.media_kind == "image"


def test_unknown_type_and_mime_leave_kind_unresolved():
    message = _normalize(_base(type="chat", hasMedia=True, media={"mimetype": "application/x-thing"}))

    assert message.media.media_kind is None


# --------------------------------------------------------------------------------------
# Robustness: malformed media must never break ingress
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "media_value",
    ["not-a-dict", 12345, [], None, {"mimetype": None, "url": None}],
)
def test_malformed_media_does_not_crash_normalization(media_value):
    message = _normalize(_base(type="image", hasMedia=True, media=media_value))

    assert message.media.mime_type is None
    assert message.media.transient_media_available is False


def test_unsafe_filename_is_dropped():
    message = _normalize(
        _base(type="document", hasMedia=True, media={"filename": "../../etc/passwd", "mimetype": "application/pdf"})
    )

    assert message.media.filename is None
    assert message.media.media_kind == "document"


def test_safe_filename_is_preserved():
    message = _normalize(
        _base(type="document", hasMedia=True, media={"filename": "report.pdf", "mimetype": "application/pdf"})
    )

    assert message.media.filename == "report.pdf"


def test_reported_size_is_best_effort_from_engine_data():
    """WAMedia has no size field, so size may only appear under engine `_data`."""
    without_size = _normalize(_base(type="image", hasMedia=True, media={"mimetype": "image/jpeg"}))
    assert without_size.media.reported_size is None

    with_size = _normalize(
        _base(type="image", hasMedia=True, media={"mimetype": "image/jpeg"}, _data={"media": {"fileSize": 2048}})
    )
    assert with_size.media.reported_size == 2048


# --------------------------------------------------------------------------------------
# Quoted source identity is a reference, never the canonical source
# --------------------------------------------------------------------------------------


def test_quoted_message_id_is_exposed_separately_from_the_canonical_source():
    message = _normalize(
        _base(id="COMMAND-1", type="chat", body=".vvopen", replyTo={"id": "TARGET-1", "hasMedia": True})
    )

    assert message.media.quoted_source_message_id == "TARGET-1"
    # The canonical source ID stays the outer event; the quote is only a pointer.
    assert message.payload["id"] == "COMMAND-1"


def test_missing_reply_context_yields_no_quoted_source():
    message = _normalize(_base(type="chat", body=".vvopen"))

    assert message.media.quoted_source_message_id is None


def test_oversized_quoted_id_is_rejected():
    message = _normalize(_base(type="chat", replyTo={"id": "x" * 400, "hasMedia": True}))

    assert message.media.quoted_source_message_id is None


def test_serialized_quoted_id_object_is_supported():
    message = _normalize(_base(type="chat", replyTo={"id": {"_serialized": "TARGET-9"}, "hasMedia": True}))

    assert message.media.quoted_source_message_id == "TARGET-9"


# --------------------------------------------------------------------------------------
# Normalization must never classify view-once
# --------------------------------------------------------------------------------------


def test_media_normalization_never_asserts_view_once():
    """View-once is decided only by ViewOnceCapabilityService from explicit evidence."""
    message = _normalize(
        _base(type="image", hasMedia=True, isViewOnce=True, media={"mimetype": "image/jpeg", "url": "http://x/a.jpg"})
    )

    assert not hasattr(message.media, "is_view_once")
    assert message.media.media_kind == "image"


def test_transient_locator_is_flagged_but_not_exposed_as_canonical_metadata():
    """The temporary URL is transport state, so only its availability is recorded."""
    message = _normalize(
        _base(type="image", hasMedia=True, media={"url": "http://waha:3000/api/files/secret.jpg", "mimetype": "image/jpeg"})
    )

    assert message.media.transient_media_available is True
    assert "secret.jpg" not in str(message.media)

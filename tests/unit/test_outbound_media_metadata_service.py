"""Canonical outbound media producer contract.

Producers must not invent their own media conventions. Everything that can attach
media to an Outbound Queue row is canonicalized here first, so the typed delivery
worker receives one consistent representation and the authority hash binds a
validated locator.
"""

from __future__ import annotations

import pytest

from app.services.outbound_media_dispatch_service import OutboundMediaDispatchService
from app.services.outbound_media_metadata_service import OutboundMediaMetadataService


def _normalize(**kwargs):
    kwargs.setdefault("media_url", "https://cdn.invalid/a.jpg")
    return OutboundMediaMetadataService.normalize(**kwargs)


# --------------------------------------------------------------------------------------
# Locator validation
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "bad_url",
    [
        None,
        "",
        "   ",
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://cdn.invalid/a.jpg",
        "https://cdn.invalid/../../secret.jpg",
        "https://cdn.invalid/%2e%2e/secret.jpg",
        "https:///no-host.jpg",
        "https://cdn.invalid/a b.jpg",
    ],
)
def test_unsafe_or_malformed_locators_are_rejected(bad_url):
    decision = OutboundMediaMetadataService.normalize(media_url=bad_url)

    assert decision.accepted is False
    assert decision.media is None


def test_oversized_locator_is_rejected():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/" + ("a" * OutboundMediaMetadataService.MAX_URL_LENGTH)
    )

    assert decision.accepted is False


def test_valid_https_locator_is_preserved_exactly():
    url = "https://cdn.invalid/path/photo.jpg?token=abc&v=2"
    decision = OutboundMediaMetadataService.normalize(media_url=url, media_kind="image")

    assert decision.accepted is True
    assert decision.media.media_url == url


# --------------------------------------------------------------------------------------
# Kind / MIME canonicalization
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("declared", "expected_kind"),
    [
        ("image", "image"),
        ("photo", "image"),
        ("gif", "image"),
        ("video", "video"),
        ("voice", "voice"),
        ("ptt", "voice"),
        ("audio", "audio"),
        ("document", "document"),
        ("file", "document"),
    ],
)
def test_producer_kind_aliases_map_to_canonical_kinds(declared, expected_kind):
    decision = _normalize(media_kind=declared, media_url="https://cdn.invalid/a.bin")

    assert decision.accepted is True
    assert decision.media.media_kind == expected_kind


def test_unknown_producer_kind_is_rejected():
    decision = _normalize(media_kind="hologram")

    assert decision.accepted is False
    assert "unsupported outbound media kind" in decision.reason


def test_extension_hint_supplies_mime_when_producer_omits_it():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/clip.mp4", media_kind="video"
    )

    assert decision.accepted is True
    assert decision.media.mimetype == "video/mp4"


def test_unknown_extension_stays_untyped_rather_than_guessing():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/thing.unknownext", media_kind="document"
    )

    assert decision.accepted is True
    assert decision.media.mimetype is None


def test_explicit_mime_conflicting_with_kind_is_rejected():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/a.bin", media_kind="video", mimetype="image/png"
    )

    assert decision.accepted is False
    assert "conflicts with MIME" in decision.reason


def test_extension_hint_conflicting_with_declared_kind_is_rejected():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/song.mp3", media_kind="video"
    )

    assert decision.accepted is False
    assert "conflicts with MIME" in decision.reason


def test_malformed_mime_is_rejected():
    decision = _normalize(media_kind="image", mimetype="notamime")

    assert decision.accepted is False


def test_unsafe_filename_is_dropped_without_rejecting_media():
    decision = _normalize(media_kind="image", filename="../../etc/passwd")

    assert decision.accepted is True
    assert decision.media.filename is None


# --------------------------------------------------------------------------------------
# Queue metadata contract
# --------------------------------------------------------------------------------------


def test_queue_metadata_carries_mime_and_provenance_for_the_worker():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/clip.mp4",
        media_kind="video",
        provenance="internet_service",
    )
    metadata = decision.media.queue_metadata()

    assert metadata["media_mime"] == "video/mp4"
    assert metadata["media_provenance"] == "internet_service"


def test_queue_metadata_never_emits_empty_optional_keys():
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://cdn.invalid/thing.unknownext", media_kind="document"
    )
    metadata = decision.media.queue_metadata()

    assert "media_mime" not in metadata
    assert "media_filename" not in metadata


# --------------------------------------------------------------------------------------
# End-to-end: canonical producer output must satisfy the typed delivery worker
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "kind", "expected_operation"),
    [
        ("https://cdn.invalid/a.jpg", "image", "send_image"),
        ("https://cdn.invalid/a.png", "image", "send_image"),
        ("https://cdn.invalid/clip.mp4", "video", "send_video"),
        ("https://cdn.invalid/note.ogg", "voice", "send_voice"),
        ("https://cdn.invalid/song.mp3", "audio", "send_file"),
        ("https://cdn.invalid/doc.pdf", "document", "send_file"),
    ],
)
def test_canonical_media_reaches_the_expected_typed_operation(url, kind, expected_operation):
    decision = OutboundMediaMetadataService.normalize(media_url=url, media_kind=kind, media_caption="cap")
    assert decision.accepted is True

    class _Row:
        media_url = decision.media.media_url
        media_type = decision.media.media_kind
        media_caption = decision.media.media_caption
        message_text = "text"
        formatting_json = decision.media.queue_metadata()

    plan = OutboundMediaDispatchService.plan(_Row())

    assert plan.allowed is True
    assert plan.plan.operation == expected_operation


def test_giphy_style_producer_output_is_canonicalized_end_to_end():
    """The live internet-service media shape must produce a typed image send."""
    decision = OutboundMediaMetadataService.normalize(
        media_url="https://media.giphy.com/media/abc/giphy.gif",
        media_kind="image",
        media_caption="Giphy: celebration",
        provenance="internet_service",
    )
    assert decision.accepted is True
    assert decision.media.mimetype == "image/gif"

    class _Row:
        media_url = decision.media.media_url
        media_type = decision.media.media_kind
        media_caption = decision.media.media_caption
        message_text = "answer"
        formatting_json = decision.media.queue_metadata()

    plan = OutboundMediaDispatchService.plan(_Row())

    assert plan.allowed is True
    assert plan.plan.operation == "send_image"
    assert plan.plan.mimetype == "image/gif"

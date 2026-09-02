"""Regressions proving outbound authority commits to exact media identity.

Before this binding, `content_sha256` covered only `message_text`. A queue row whose
media columns changed after OWNER approval still produced the identical digest, so an
approval granted for one attachment authorized delivery of a different one. These tests
pin the fail-closed behaviour while keeping existing text-only authority byte-identical.
"""

from __future__ import annotations

from types import SimpleNamespace

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.owner_outbound_approval_service import OwnerOutboundApprovalService


def _media_message(
    *,
    message_id: int = 10,
    chat_id: str = "222@c.us",
    text: str = "See this",
    media_url: str | None = "https://waha.invalid/files/approved.jpg",
    media_type: str | None = "image",
    media_caption: str | None = "See this",
    metadata: dict | None = None,
):
    return SimpleNamespace(
        id=message_id,
        chat_id=chat_id,
        message_text=text,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        formatting_json=metadata,
    )


def _stamped(message) -> dict:
    return {
        "inbound_message_id": 5,
        "contact_id": 7,
        "response_category": "normal_reply",
        "content_sha256": OutboundAuthorizationService.content_hash_for_message(message),
    }


def test_text_only_authority_digest_is_unchanged_for_existing_approvals():
    """Durable approvals stamped before media binding must remain valid."""
    text = "hello"
    message = _media_message(text=text, media_url=None, media_type=None, media_caption=None)

    assert OutboundAuthorizationService.content_hash_for_message(message) == (
        OutboundAuthorizationService.content_hash(text)
    )

    message.formatting_json = {
        "inbound_message_id": 5,
        "contact_id": 7,
        "response_category": "normal_reply",
        "content_sha256": OutboundAuthorizationService.content_hash(text),
    }
    assert OutboundAuthorizationService.context_from_queue_message(message) is not None


def test_whatsapp_formatting_is_preserved_exactly_in_text_only_digest():
    formatted = "> quoted text\n\n*emphasis* uses `inline code`.\n\nFinal paragraph."

    assert OutboundAuthorizationService.authority_content_hash(formatted) == (
        OutboundAuthorizationService.content_hash(formatted)
    )
    assert OutboundAuthorizationService.authority_content_hash(
        formatted.replace("\n\n", "\n")
    ) != OutboundAuthorizationService.content_hash(formatted)


def test_authorized_media_row_passes_the_fence_when_media_is_unchanged():
    message = _media_message()
    message.formatting_json = _stamped(message)

    context = OutboundAuthorizationService.context_from_queue_message(message)

    assert context is not None
    assert context.target_chat_id == "222@c.us"


def test_swapped_media_url_invalidates_existing_authority():
    """The exact private-media escalation this binding exists to prevent."""
    message = _media_message()
    message.formatting_json = _stamped(message)
    assert OutboundAuthorizationService.context_from_queue_message(message) is not None

    message.media_url = "https://waha.invalid/files/private-view-once.mp4"

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_swapped_media_kind_invalidates_existing_authority():
    message = _media_message()
    message.formatting_json = _stamped(message)

    message.media_type = "video"

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_changed_media_caption_invalidates_existing_authority():
    message = _media_message()
    message.formatting_json = _stamped(message)

    message.media_caption = "different caption sent to the contact"

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_attaching_media_to_an_approved_text_only_row_invalidates_authority():
    message = _media_message(media_url=None, media_type=None, media_caption=None)
    message.formatting_json = _stamped(message)
    assert OutboundAuthorizationService.context_from_queue_message(message) is not None

    message.media_url = "https://waha.invalid/files/private-view-once.mp4"
    message.media_type = "video"

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_removing_approved_media_invalidates_authority():
    message = _media_message()
    message.formatting_json = _stamped(message)

    message.media_url = None
    message.media_type = None
    message.media_caption = None

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_distinct_media_identities_never_share_one_digest():
    base = OutboundAuthorizationService.authority_content_hash(
        "caption", media_url="https://waha.invalid/a.jpg", media_type="image"
    )
    other_url = OutboundAuthorizationService.authority_content_hash(
        "caption", media_url="https://waha.invalid/b.jpg", media_type="image"
    )
    other_kind = OutboundAuthorizationService.authority_content_hash(
        "caption", media_url="https://waha.invalid/a.jpg", media_type="video"
    )

    assert len({base, other_url, other_kind}) == 3


def test_media_field_boundaries_cannot_be_confused_by_concatenation():
    """Field separation must be structural, not string concatenation."""
    first = OutboundAuthorizationService.authority_content_hash(
        "a", media_url="b", media_type="c"
    )
    shifted = OutboundAuthorizationService.authority_content_hash(
        "ab", media_url="", media_type="c"
    )

    assert first != shifted


def _approval_row(
    *,
    text_value: str = "See this",
    media_url: str | None = "https://waha.invalid/files/approved.jpg",
    media_type: str | None = "image",
    media_caption: str | None = "See this",
) -> dict:
    digest = OutboundAuthorizationService.authority_content_hash(
        text_value,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
    )
    return {
        "id": 41,
        "inbound_message_id": 5,
        "outbound_queue_id": 10,
        "target_chat_id": "222@c.us",
        "content_sha256": digest,
        "status": "pending",
        "queue_chat_id": "222@c.us",
        "message_text": text_value,
        "media_url": media_url,
        "media_type": media_type,
        "media_caption": media_caption,
        "queue_status": "deferred",
        "formatting_json": {
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
            "delivery_policy": "approval_required",
        },
    }


def test_owner_approval_path_accepts_exact_unchanged_media_binding():
    assert OwnerOutboundApprovalService._authority_mismatch(_approval_row()) is None


def test_owner_approval_path_rejects_media_swapped_after_stamping():
    row = _approval_row()
    row["media_url"] = "https://waha.invalid/files/private-view-once.mp4"

    mismatch = OwnerOutboundApprovalService._authority_mismatch(row)

    assert mismatch is not None
    assert "content hash" in mismatch


def test_owner_approval_path_still_accepts_legacy_text_only_rows():
    row = _approval_row(media_url=None, media_type=None, media_caption=None)

    assert row["content_sha256"] == OutboundAuthorizationService.content_hash("See this")
    assert OwnerOutboundApprovalService._authority_mismatch(row) is None

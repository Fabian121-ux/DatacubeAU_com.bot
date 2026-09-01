"""Media-type-aware outbound dispatch regressions.

Every case uses mocked transports. No real WhatsApp send, WAHA reconnect, or session
mutation occurs. These tests pin two guarantees:

1. an authorized media row reaches exactly one correct typed WAHA operation, and
2. dispatch can only narrow behaviour -- it never becomes an authorization mechanism.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from app.models.schema import OutboundMessage
from app.services.outbound_authorization_service import (
    AuthorizationDecision,
    OutboundAuthorizationService,
)
from app.services.outbound_media_dispatch_service import OutboundMediaDispatchService
from app.services.outbound_safety_limit_service import OutboundSafetyDecision
from app.services.waha_client import WahaClientError
from app.utils.time import utcnow
from app.workers import background_workers


OWNER_CHAT = "111@c.us"


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _RecordingClient:
    """Records every transport call so we can assert exact operation and call count."""

    def __init__(self, *, fail: Exception | None = None):
        self.calls: list[tuple[str, dict]] = []
        self.fail = fail

    def _record(self, operation, chat_id, kwargs):
        self.calls.append((operation, {"chatId": chat_id, **kwargs}))
        if self.fail is not None:
            raise self.fail
        return {"id": f"mock-{operation}"}

    async def send_text(self, *, chat_id, text):
        return self._record("send_text", chat_id, {"text": text})

    async def send_media(self, *, chat_id, media_url, caption=None):
        return self._record("send_media", chat_id, {"url": media_url, "caption": caption})

    async def send_image(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        return self._record(
            "send_image", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption, "filename": filename}
        )

    async def send_video(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        return self._record(
            "send_video", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption, "filename": filename}
        )

    async def send_voice(self, chat_id, *, media_url, mimetype, filename=None):
        return self._record("send_voice", chat_id, {"url": media_url, "mimetype": mimetype, "filename": filename})

    async def send_file(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        return self._record(
            "send_file", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption, "filename": filename}
        )


async def _queue_owner_media_row(db_session, *, media_type, media_mime, media_url="https://waha.invalid/files/a.bin"):
    """Owner self-DM row: the fence authorizes it, isolating dispatch behaviour."""
    now = utcnow()
    metadata = {}
    if media_mime is not None:
        metadata["media_mime"] = media_mime
    row = OutboundMessage(
        chat_id=OWNER_CHAT,
        message_text="caption text",
        media_url=media_url,
        media_type=media_type,
        media_caption="caption text",
        formatting_json=metadata,
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()
    return row


def _use_session(monkeypatch, db_session):
    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_CHAT)


# --------------------------------------------------------------------------------------
# Correct typed transport selection
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "media_mime", "expected_operation"),
    [
        ("image", "image/jpeg", "send_image"),
        ("video", "video/mp4", "send_video"),
        ("voice", "audio/ogg", "send_voice"),
        ("ptt", "audio/ogg", "send_voice"),
        ("audio", "audio/mpeg", "send_file"),
        ("document", "application/pdf", "send_file"),
    ],
)
async def test_authorized_media_invokes_exact_typed_operation_once(
    db_session, monkeypatch, media_type, media_mime, expected_operation
):
    row = await _queue_owner_media_row(db_session, media_type=media_type, media_mime=media_mime)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert len(client.calls) == 1
    operation, payload = client.calls[0]
    assert operation == expected_operation
    assert payload["mimetype"] == media_mime
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_video_never_uses_the_image_or_legacy_media_endpoint(db_session, monkeypatch):
    row = await _queue_owner_media_row(db_session, media_type="video", media_mime="video/mp4")
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)
    await db_session.refresh(row)

    operations = [operation for operation, _ in client.calls]
    assert operations == ["send_video"]
    assert "send_image" not in operations
    assert "send_media" not in operations


# --------------------------------------------------------------------------------------
# Fail-closed media validation: zero WAHA calls
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unknown_media_kind_makes_zero_waha_calls(db_session, monkeypatch):
    row = await _queue_owner_media_row(db_session, media_type="hologram", media_mime="image/png")
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "unknown outbound media kind" in (row.error_message or "")


@pytest.mark.asyncio
async def test_mime_and_type_conflict_makes_zero_waha_calls(db_session, monkeypatch):
    row = await _queue_owner_media_row(db_session, media_type="video", media_mime="image/png")
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "conflicts with MIME" in (row.error_message or "")


@pytest.mark.asyncio
async def test_typed_non_image_media_without_mime_makes_zero_waha_calls(db_session, monkeypatch):
    """Without a MIME a video row must never fall back to the legacy image path."""
    row = await _queue_owner_media_row(db_session, media_type="video", media_mime=None)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "requires an explicit MIME type" in (row.error_message or "")


@pytest.mark.asyncio
async def test_malformed_mime_makes_zero_waha_calls(db_session, monkeypatch):
    row = await _queue_owner_media_row(db_session, media_type="image", media_mime="not-a-mime")
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"


# --------------------------------------------------------------------------------------
# Authorization remains upstream of dispatch
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unauthorized_media_row_makes_zero_waha_calls(db_session, monkeypatch):
    """An external media row with no durable authority never reaches dispatch."""
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="caption",
        media_url="https://waha.invalid/files/private.mp4",
        media_type="video",
        media_caption="caption",
        formatting_json={"media_mime": "video/mp4"},
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "missing explicit durable outbound authority" in (row.error_message or "")


@pytest.mark.asyncio
async def test_expired_authority_makes_zero_waha_calls(db_session, monkeypatch):
    now = utcnow()
    text_value = "caption"
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text_value,
        media_url="https://waha.invalid/files/a.jpg",
        media_type="image",
        media_caption=text_value,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": 41,
            "contact_id": 42,
            "media_mime": "image/jpeg",
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    row.formatting_json["content_sha256"] = OutboundAuthorizationService.content_hash_for_message(row)
    db_session.add(row)
    await db_session.commit()

    async def _expired(self, message, *, now=None):
        return None, AuthorizationDecision(False, "none", "approval expired")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _expired)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "expired" in (row.error_message or "")


@pytest.mark.asyncio
async def test_media_swapped_after_approval_makes_zero_waha_calls(db_session, monkeypatch):
    """The media-binding hash must still invalidate authority at the worker."""
    now = utcnow()
    text_value = "caption"
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text_value,
        media_url="https://waha.invalid/files/approved.jpg",
        media_type="image",
        media_caption=text_value,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": 41,
            "contact_id": 42,
            "media_mime": "image/jpeg",
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    row.formatting_json["content_sha256"] = OutboundAuthorizationService.content_hash_for_message(row)
    db_session.add(row)
    await db_session.commit()

    # Swap the artifact after the authority stamp, leaving the text untouched.
    row.media_url = "https://waha.invalid/files/private-view-once.mp4"
    await db_session.commit()

    called = False

    async def _would_allow(self, context, *, now=None):
        nonlocal called
        called = True
        return AuthorizationDecision(True, "owner_approval", "should never be consulted")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize", _would_allow)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert called is False
    assert row.status == "deferred"
    assert "content hash mismatch" in (row.error_message or "")


@pytest.mark.asyncio
async def test_dispatch_cannot_authorize_a_row_the_safety_limits_rejected(db_session, monkeypatch):
    now = utcnow()
    text_value = "caption"
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text_value,
        media_url="https://waha.invalid/files/a.jpg",
        media_type="image",
        media_caption=text_value,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": 41,
            "contact_id": 42,
            "media_mime": "image/jpeg",
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    row.formatting_json["content_sha256"] = OutboundAuthorizationService.content_hash_for_message(row)
    db_session.add(row)
    await db_session.commit()

    async def _authorized(self, message, *, now=None):
        return self.context_from_queue_message(message), AuthorizationDecision(
            True, "owner_approval", "exact active owner approval", approval_id=None
        )

    async def _rate_limited(self, message, *, now=None):
        return OutboundSafetyDecision(False, "bounded outbound safety limit reached")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _rate_limited)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert client.calls == []
    assert row.status == "deferred"
    assert "safety limit" in (row.error_message or "")


# --------------------------------------------------------------------------------------
# Uncertain outcomes and text-only behaviour
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncertain_typed_media_result_is_not_blindly_retried(db_session, monkeypatch):
    row = await _queue_owner_media_row(db_session, media_type="video", media_mime="video/mp4")
    _use_session(monkeypatch, db_session)
    client = _RecordingClient(fail=WahaClientError("connection closed before response"))

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert len(client.calls) == 1
    assert row.status == "deferred"
    assert row.retry_count == 0
    assert "automatic replay blocked" in (row.error_message or "")

    # A later worker pass must not resend a row whose outcome is unknown.
    second = await background_workers._deliver_due_outbound_messages(client)
    await db_session.refresh(row)
    assert second == 0
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_text_only_delivery_behaviour_is_unchanged(db_session, monkeypatch):
    now = utcnow()
    text_value = "> quoted line\n\n*Important* uses `inline code`.\n\nFinal paragraph."
    row = OutboundMessage(
        chat_id=OWNER_CHAT,
        message_text=text_value,
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == [("send_text", {"chatId": OWNER_CHAT, "text": text_value})]
    assert row.message_text == text_value
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_legacy_untyped_media_row_keeps_existing_image_only_delivery(db_session, monkeypatch):
    """Rows created before typed media must not change behaviour or start failing."""
    row = await _queue_owner_media_row(db_session, media_type=None, media_mime=None)
    _use_session(monkeypatch, db_session)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert [operation for operation, _ in client.calls] == ["send_media"]
    assert row.status == "sent"


# --------------------------------------------------------------------------------------
# Planner-level unit checks
# --------------------------------------------------------------------------------------


def test_planner_never_returns_a_plan_without_a_media_locator():
    class _Row:
        media_url = ""
        media_type = "image"
        media_caption = "c"
        message_text = "t"
        formatting_json = {"media_mime": "image/jpeg"}

    decision = OutboundMediaDispatchService.plan(_Row())

    assert decision.allowed is False


def test_planner_rejects_unsafe_filenames_without_blocking_delivery():
    class _Row:
        media_url = "https://waha.invalid/files/a.jpg"
        media_type = "image"
        media_caption = "c"
        message_text = "t"
        formatting_json = {"media_mime": "image/jpeg", "media_filename": "../../etc/passwd"}

    decision = OutboundMediaDispatchService.plan(_Row())

    assert decision.allowed is True
    assert decision.plan.filename is None


def test_planner_requires_explicit_kind_for_ambiguous_audio():
    class _Row:
        media_url = "https://waha.invalid/files/a.ogg"
        media_type = None
        media_caption = "c"
        message_text = "t"
        formatting_json = {"media_mime": "audio/ogg"}

    decision = OutboundMediaDispatchService.plan(_Row())

    assert decision.allowed is False
    assert "explicit voice or audio kind" in decision.reason

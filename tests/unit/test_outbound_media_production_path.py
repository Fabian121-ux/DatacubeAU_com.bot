"""End-to-end outbound media production path.

The dispatch regressions start from a hand-built Outbound Queue row, which proves the
worker half of the pipeline but assumes a producer can actually create such a row. These
tests close that gap by driving a real `PlannedReply` through the real router into the
real delivery worker:

    producer (PlannedReply)
      -> router canonicalization
      -> OutboundMessage
      -> authority hash
      -> final authorization fence
      -> safety limits
      -> typed dispatch
      -> WAHA adapter

Only the AI planner and the WAHA transport are replaced. Everything between them is
production code. No real WhatsApp transport is contacted.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.reply_planner import PlannedReply
from app.core.router import InboundRouter
from app.models.enums import DecisionType
from app.models.schema import Contact, OutboundMessage
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.waha_client import WahaClientError
from app.workers import background_workers


OWNER_CHAT = "2348000000001@c.us"


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _RecordingClient:
    """Records the exact WAHA operation and payload for each delivery."""

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
        return self._record("send_image", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption})

    async def send_video(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        return self._record("send_video", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption})

    async def send_voice(self, chat_id, *, media_url, mimetype, filename=None):
        return self._record("send_voice", chat_id, {"url": media_url, "mimetype": mimetype})

    async def send_file(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        return self._record("send_file", chat_id, {"url": media_url, "mimetype": mimetype, "caption": caption})


def _event(chat_id=OWNER_CHAT, message_id="PROD-1", body="show me"):
    return {
        "event": "message",
        "session": "test",
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": False,
            "body": body,
        },
    }


def _planned(*, media_url=None, media_type=None, media_caption=None, text="here you go"):
    return PlannedReply(
        decision_type=DecisionType.STATIC_REPLY,
        reason="media production path test",
        should_reply=True,
        reply_text=text,
        raw_reply_text=text,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        source_diagnostics={"source": "internet_service"},
    )


async def _run_producer(db_session, monkeypatch, planned, *, chat_id=OWNER_CHAT, message_id="PROD-1"):
    """Drive the real router with a stubbed planner and return the created queue row."""
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_CHAT)
    monkeypatch.setattr("app.core.router.settings.owner_whatsapp_ids", OWNER_CHAT)

    router = InboundRouter(db_session)

    async def _plan(*args, **kwargs):
        return planned

    monkeypatch.setattr(router.reply_planner, "plan", _plan)
    monkeypatch.setattr(router.reply_planner, "cache_answer_if_reusable", _noop)
    monkeypatch.setattr(router.reply_planner, "upsert_conversation_summary", _noop)
    monkeypatch.setattr(router, "_maybe_typing_delay", _noop)

    await router.process_event(_event(chat_id=chat_id, message_id=message_id))
    await db_session.commit()

    return (
        await db_session.execute(select(OutboundMessage).order_by(OutboundMessage.id.desc()).limit(1))
    ).scalar_one()


async def _noop(*args, **kwargs):
    return None


async def _deliver(db_session, monkeypatch, client):
    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    return await background_workers._deliver_due_outbound_messages(client)


# --------------------------------------------------------------------------------------
# Typed producer -> typed WAHA operation
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_url", "media_type", "expected_operation", "expected_mime"),
    [
        ("https://cdn.invalid/photo.jpg", "image", "send_image", "image/jpeg"),
        ("https://cdn.invalid/clip.mp4", "video", "send_video", "video/mp4"),
        ("https://cdn.invalid/note.ogg", "voice", "send_voice", "audio/ogg"),
        ("https://cdn.invalid/song.mp3", "audio", "send_file", "audio/mpeg"),
        ("https://cdn.invalid/report.pdf", "document", "send_file", "application/pdf"),
    ],
)
async def test_producer_media_reaches_exact_typed_waha_operation(
    db_session, monkeypatch, media_url, media_type, expected_operation, expected_mime
):
    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url=media_url, media_type=media_type, media_caption="look"),
    )

    # The router must have canonicalized the producer's media before queueing.
    assert row.media_url == media_url
    assert row.formatting_json["media_mime"] == expected_mime
    assert row.formatting_json["media_provenance"] == "internet_service"

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert len(client.calls) == 1
    operation, payload = client.calls[0]
    assert operation == expected_operation
    assert payload["mimetype"] == expected_mime
    assert payload["chatId"] == OWNER_CHAT
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_producer_video_never_reaches_the_image_endpoint(db_session, monkeypatch):
    await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url="https://cdn.invalid/clip.mp4", media_type="video"),
    )
    client = _RecordingClient()

    await _deliver(db_session, monkeypatch, client)

    operations = [operation for operation, _ in client.calls]
    assert operations == ["send_video"]
    assert "send_image" not in operations
    assert "send_media" not in operations


# --------------------------------------------------------------------------------------
# Malformed producer metadata must not reach the transport as media
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_url", "media_type"),
    [
        ("javascript:alert(1)", "image"),
        ("file:///etc/passwd", "image"),
        ("https://cdn.invalid/../../secret.jpg", "image"),
        ("https://cdn.invalid/a.jpg", "hologram"),
        ("https://cdn.invalid/song.mp3", "video"),
    ],
)
async def test_malformed_producer_media_is_dropped_before_the_queue(
    db_session, monkeypatch, media_url, media_type
):
    """Unsafe or contradictory media is dropped; the text reply still stands."""
    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url=media_url, media_type=media_type, text="still a valid reply"),
    )

    assert row.media_url is None
    assert row.media_type is None
    assert "media_mime" not in (row.formatting_json or {})

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    # It degrades to a text send, never a media send with an unvalidated locator.
    assert [operation for operation, _ in client.calls] == ["send_text"]


# --------------------------------------------------------------------------------------
# Authority binding across the real producer path
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_producer_media_row_is_authority_bound_to_its_exact_media(db_session, monkeypatch):
    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url="https://cdn.invalid/photo.jpg", media_type="image", media_caption="look"),
    )

    expected = OutboundAuthorizationService.content_hash_for_message(row)
    # Owner rows are authorized by exact-chat match rather than an approval hash, but the
    # digest must still be derivable and media-sensitive for external rows.
    swapped = SimpleNamespace(
        message_text=row.message_text,
        media_url="https://cdn.invalid/other.jpg",
        media_type=row.media_type,
        media_caption=row.media_caption,
    )
    assert OutboundAuthorizationService.content_hash_for_message(swapped) != expected


@pytest.mark.asyncio
async def test_external_producer_media_requires_approval_before_any_send(db_session, monkeypatch):
    """An external contact's media reply must never auto-send."""
    contact = Contact(whatsapp_id="2348000000002@c.us", chat_id="2348000000002@c.us", display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()

    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url="https://cdn.invalid/photo.jpg", media_type="image"),
        chat_id="2348000000002@c.us",
        message_id="PROD-EXT-1",
    )

    assert row.status == "deferred"
    assert row.formatting_json["delivery_policy"] == "approval_required"

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    assert client.calls == []


@pytest.mark.asyncio
async def test_media_swapped_after_queueing_blocks_external_delivery(db_session, monkeypatch):
    contact = Contact(whatsapp_id="2348000000002@c.us", chat_id="2348000000002@c.us", display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()

    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url="https://cdn.invalid/approved.jpg", media_type="image"),
        chat_id="2348000000002@c.us",
        message_id="PROD-EXT-2",
    )

    # Swap the artifact after the authority stamp, then force the row eligible.
    row.media_url = "https://cdn.invalid/private-view-once.mp4"
    row.status = "pending"
    await db_session.commit()

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert client.calls == []
    assert row.status == "deferred"


# --------------------------------------------------------------------------------------
# Transport failure and text-only parity
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncertain_media_send_is_not_blindly_retried(db_session, monkeypatch):
    row = await _run_producer(
        db_session,
        monkeypatch,
        _planned(media_url="https://cdn.invalid/clip.mp4", media_type="video"),
    )
    client = _RecordingClient(fail=WahaClientError("connection closed before response"))

    await _deliver(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert len(client.calls) == 1
    assert row.status == "deferred"
    assert row.retry_count == 0
    assert "automatic replay blocked" in (row.error_message or "")

    await _deliver(db_session, monkeypatch, client)
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_text_only_producer_path_is_unchanged(db_session, monkeypatch):
    text = "> quoted line\n\n*Important* uses `inline code`.\n\nFinal paragraph."
    row = await _run_producer(db_session, monkeypatch, _planned(text=text))

    assert row.media_url is None

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert client.calls == [("send_text", {"chatId": OWNER_CHAT, "text": text})]
    assert row.message_text == text
    assert row.status == "sent"

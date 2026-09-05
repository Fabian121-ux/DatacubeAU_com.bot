"""Owner-destined outbound rows must stay bound to their authorized payload.

The delivery fence proves the OWNER destination by exact configured chat id. That is a
statement about *where* a row may go, not about *what* it may carry. Without a payload
binding, anything that can write to an owner-destined queue row between creation and
delivery gains full send authority over the owner's own inbox.

These tests drive the real delivery worker with a recording transport, so a "zero WAHA
calls" assertion is a statement about the real send path rather than about a helper.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.schema import OutboundMessage
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.waha_client import WahaClientError
from app.workers import background_workers


OWNER_CHAT = "2348000000001@c.us"
EXTERNAL_CHAT = "2348000000002@c.us"
MEDIA_URL = "http://waha:3000/api/files/original.jpg"


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


@pytest.fixture(autouse=True)
def _owner_configured(monkeypatch):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_CHAT)


async def _deliver(db_session, monkeypatch, client):
    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    return await background_workers._deliver_due_outbound_messages(client)


async def _queue(
    db_session,
    *,
    chat_id=OWNER_CHAT,
    text="original owner text",
    media_url=None,
    media_type=None,
    media_caption=None,
    formatting=None,
    stamp=True,
):
    """Create a queue row the way a production producer does, then stamp it."""
    row = OutboundMessage(
        chat_id=chat_id,
        message_text=text,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        formatting_json=dict(formatting or {"source": "owner_push", "command": ".push"}),
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(row)
    await db_session.flush()
    if stamp:
        row.formatting_json = OutboundAuthorizationService.stamp_owner_payload(row)
    await db_session.commit()
    return row


# --------------------------------------------------------------------------------------
# The authorized original must still be delivered exactly once.
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_authorized_owner_text_delivers_exactly_once(db_session, monkeypatch):
    row = await _queue(db_session, text="hello owner")
    client = _RecordingClient()

    processed = await _deliver(db_session, monkeypatch, client)

    assert processed == 1
    assert client.calls == [("send_text", {"chatId": OWNER_CHAT, "text": "hello owner"})]
    assert row.status == "sent"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "mimetype", "expected_operation"),
    [
        ("image", "image/jpeg", "send_image"),
        ("video", "video/mp4", "send_video"),
        ("voice", "audio/ogg", "send_voice"),
        ("file", "application/pdf", "send_file"),
    ],
)
async def test_authorized_owner_media_uses_exact_typed_dispatch(
    db_session, monkeypatch, media_type, mimetype, expected_operation
):
    await _queue(
        db_session,
        media_url=MEDIA_URL,
        media_type=media_type,
        media_caption="original caption",
        formatting={"source": "owner_push", "media_mime": mimetype},
    )
    client = _RecordingClient()

    await _deliver(db_session, monkeypatch, client)

    assert [call[0] for call in client.calls] == [expected_operation]
    assert client.calls[0][1]["chatId"] == OWNER_CHAT


# --------------------------------------------------------------------------------------
# Payload mutation after authority must reach WAHA zero times.
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("message_text", "attacker replaced this text"),
        ("chat_id", EXTERNAL_CHAT),
        ("media_url", "http://waha:3000/api/files/swapped.jpg"),
        ("media_type", "video"),
        ("media_caption", "attacker caption"),
    ],
)
async def test_mutated_owner_payload_makes_zero_waha_calls(db_session, monkeypatch, field, value):
    row = await _queue(
        db_session,
        media_url=MEDIA_URL,
        media_type="image",
        media_caption="original caption",
        formatting={"source": "owner_push", "media_mime": "image/jpeg"},
    )

    setattr(row, field, value)
    await db_session.commit()

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    assert client.calls == []
    await db_session.refresh(row)
    assert row.status != "sent"


@pytest.mark.asyncio
async def test_text_only_owner_row_mutation_makes_zero_waha_calls(db_session, monkeypatch):
    """Text-only rows keep the legacy digest, and must still be bound by it."""
    row = await _queue(db_session, text="original owner text")

    row.message_text = "attacker replaced this text"
    await db_session.commit()

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    assert client.calls == []


@pytest.mark.asyncio
async def test_attaching_media_to_a_stamped_text_row_makes_zero_waha_calls(db_session, monkeypatch):
    """Owner destination must not permit smuggling an attachment onto a text row."""
    row = await _queue(db_session, text="original owner text")

    row.media_url = MEDIA_URL
    row.media_type = "image"
    await db_session.commit()

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    assert client.calls == []


@pytest.mark.asyncio
async def test_owner_destination_alone_is_not_delivery_authority(db_session, monkeypatch):
    """The fence must consult the payload binding, not only the destination."""
    row = await _queue(db_session, text="original owner text")
    row.message_text = "mutated"
    await db_session.commit()

    allowed, reason, approval_id = await background_workers._delivery_authorized(
        db_session, OutboundAuthorizationService(db_session), row
    )

    assert allowed is False
    assert "mutated" in reason or "payload" in reason
    assert approval_id is None


# --------------------------------------------------------------------------------------
# Delivery semantics that must not regress.
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_uncertain_owner_send_is_not_blindly_retried(db_session, monkeypatch):
    row = await _queue(db_session, text="uncertain owner text")
    client = _RecordingClient(fail=WahaClientError("timeout"))

    await _deliver(db_session, monkeypatch, client)
    first = len(client.calls)
    await _deliver(db_session, monkeypatch, client)

    assert first == 1
    assert len(client.calls) == 1
    await db_session.refresh(row)
    assert row.status == "deferred"


@pytest.mark.asyncio
async def test_already_sent_owner_row_is_not_resent(db_session, monkeypatch):
    row = await _queue(db_session, text="already delivered")
    client = _RecordingClient()

    await _deliver(db_session, monkeypatch, client)
    await _deliver(db_session, monkeypatch, client)

    assert len(client.calls) == 1
    await db_session.refresh(row)
    assert row.status == "sent"


@pytest.mark.asyncio
async def test_stamp_is_stable_and_does_not_discard_producer_metadata(db_session):
    row = await _queue(db_session, formatting={"source": "owner_push", "command": ".push"})

    assert row.formatting_json["source"] == "owner_push"
    assert row.formatting_json["command"] == ".push"
    # Re-stamping identical content is idempotent.
    assert (
        OutboundAuthorizationService.stamp_owner_payload(row)[
            OutboundAuthorizationService.OWNER_PAYLOAD_KEY
        ]
        == row.formatting_json[OutboundAuthorizationService.OWNER_PAYLOAD_KEY]
    )


@pytest.mark.asyncio
async def test_stamp_binds_recipient_so_it_cannot_be_replayed_to_another_chat(db_session):
    """The digest must commit to the recipient, not only the content."""
    row = await _queue(db_session, text="same text")
    original = row.formatting_json[OutboundAuthorizationService.OWNER_PAYLOAD_KEY]

    row.chat_id = EXTERNAL_CHAT

    assert (
        OutboundAuthorizationService.owner_payload_digest(row) != original
    )


# --------------------------------------------------------------------------------------
# Every owner-capable producer must stamp its rows.
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_every_owner_destined_producer_row_is_bound(db_session, monkeypatch):
    """Guards against a producer being added or changed without a payload binding.

    Any owner-destined row reaching the queue unstamped is refused at the fence, so this
    asserts the positive obligation at the producer rather than only the fence's refusal.
    """
    from app.models.schema import AdminAccount
    from app.core.message_normalizer import MessageNormalizer
    from app.services.push_command_service import PushCommandService

    owner = AdminAccount(
        name="Fabian",
        whatsapp_number=OWNER_CHAT.split("@")[0],
        normalized_whatsapp_id=OWNER_CHAT,
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()

    event = {
        "event": "message.any",
        "session": "test",
        "payload": {
            "id": "PUSH-BIND-1",
            "chatId": EXTERNAL_CHAT,
            "from": EXTERNAL_CHAT,
            "fromMe": True,
            "body": ".push",
            "replyTo": {"id": "SRC-BIND-1", "body": "source text", "hasMedia": False},
        },
    }
    normalized = MessageNormalizer().normalize(event)
    await PushCommandService(db_session).handle(
        normalized, owner=owner, transport_message_id="PUSH-BIND-1"
    )
    await db_session.commit()

    rows = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert rows, "the push producer should have queued an owner-destined row"
    for row in rows:
        assert row.chat_id == OWNER_CHAT
        assert OutboundAuthorizationService.owner_payload_matches(row), (
            "owner-destined producer row is not payload-bound"
        )

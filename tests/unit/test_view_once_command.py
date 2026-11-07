"""OWNER-only view-once command family.

The handler is capability inspection plus queueing, never authority. It makes no WAHA
call, and every row it creates still passes the existing P0 final authorization fence.

Media is returned only when an exact same-source transient capability exists in the
OWNER's own reply payload at command time. A historical observation alone can never
produce a send, because the durable record deliberately stores no locator.
"""

from __future__ import annotations

import asyncio
import os

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, AuditLog, OutboundMessage
from app.services.command_control_service import CommandControlService
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.view_once_command_service import ViewOnceCommandService
from app.services.waha_client import WahaClientError
from app.workers import background_workers


OWNER_ID = "2348000000001@c.us"
PEER_ID = "2348000000002@c.us"
TRUSTED_URL = "http://waha:3000/api/files/view-once.jpg"


def _owner(permission="owner", primary=True):
    return AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id=OWNER_ID,
        role="primary_admin",
        permission_level=permission,
        is_primary=primary,
        is_enabled=True,
    )


def _event(
    *,
    body="@Zina .vvopen",
    command_id="VV-CMD-1",
    quoted_id="SRC-1",
    view_once=True,
    media_url=TRUSTED_URL,
    mimetype="image/jpeg",
    media_type="image",
    chat_id=PEER_ID,
    from_me=True,
):
    payload = {
        "id": command_id,
        "chatId": chat_id,
        "from": chat_id,
        "fromMe": from_me,
        "body": body,
    }
    if quoted_id is not None:
        reply = {"id": quoted_id, "hasMedia": True}
        if view_once is not None:
            reply["isViewOnce"] = view_once
        media = {}
        if media_url:
            media["url"] = media_url
        if mimetype:
            media["mimetype"] = mimetype
        if media_type:
            media["type"] = media_type
        if media:
            reply["media"] = media
        payload["replyTo"] = reply
    return {"event": "message.any", "session": "default", "payload": payload}


def _normalize(event):
    return MessageNormalizer().normalize(event)


async def _seed_owner(db_session, permission="owner"):
    owner = _owner(permission=permission)
    db_session.add(owner)
    await db_session.flush()
    return owner


async def _seed_metadata(db_session, *, source_id="SRC-1", deleted=False, transport=True):
    await db_session.execute(
        text(
            """
            INSERT INTO view_once_media_metadata (
                source_message_id, source_chat_id, media_type, media_mime,
                capability_state, evidence_source, transport_available, retention_mode,
                deleted_at
            ) VALUES (
                :sid, :chat, 'image', 'image/jpeg',
                'transient_available', 'waha_payload', :transport, 'none',
                CASE WHEN :deleted THEN now() ELSE NULL END
            )
            """
        ),
        {"sid": source_id, "chat": PEER_ID, "transport": transport, "deleted": deleted},
    )


async def _outbound(db_session):
    return (await db_session.execute(select(OutboundMessage))).scalars().all()


async def _run(db_session, event, owner, operation=None):
    message = _normalize(event)
    command, args = CommandControlService.parse(message.message_text)
    resolved = operation or CommandControlService._view_once_operation(command, args)
    return await ViewOnceCommandService(db_session).handle(
        resolved,
        message=message,
        owner=owner,
        transport_message_id=event["payload"]["id"],
    )


# --------------------------------------------------------------------------------------
# Alias resolution
# --------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("command", "args", "expected"),
    [
        (".vv", "", "open"),
        (".vvopen", "", "open"),
        ("/vvopen", "", "open"),
        (".vv", "info", "info"),
        (".vv", "list", "list"),
        (".vv", "delete", "delete"),
        (".vvretain", "off", "retain_off"),
        (".vvretain", "on", "retain_on"),
    ],
)
def test_every_alias_resolves_to_one_operation(command, args, expected):
    assert CommandControlService._view_once_operation(command, args) == expected


def test_unrelated_commands_are_not_view_once():
    assert CommandControlService._view_once_operation(".push", "") is None
    assert CommandControlService._view_once_operation(".commands", "") is None


# --------------------------------------------------------------------------------------
# Exact source correlation
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_missing_reply_context_does_not_guess(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(quoted_id=None), owner)

    assert "Reply directly to the target message" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_unobserved_source_is_not_opened(db_session):
    owner = await _seed_owner(db_session)

    result = await _run(db_session, _event(quoted_id="NEVER-SEEN"), owner)

    assert "has not observed" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_quoted_evidence_disagreeing_with_source_is_denied(db_session):
    """The detector's own ID must match the quoted source it is attached to."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session, source_id="SRC-1")
    event = _event(quoted_id="SRC-1")
    # A conflicting nested ID inside the same snapshot must fail closed.
    event["payload"]["replyTo"]["_data"] = {"id": "DIFFERENT-SOURCE"}

    result = await _run(db_session, event, owner)

    assert await _outbound(db_session) == []
    assert result.reply_text is not None


@pytest.mark.asyncio
async def test_oversized_quoted_id_is_rejected(db_session):
    owner = await _seed_owner(db_session)

    result = await _run(db_session, _event(quoted_id="x" * 400), owner)

    assert "Reply directly to the target message" in result.reply_text


# --------------------------------------------------------------------------------------
# Capability truth
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_ordinary_media_is_not_claimed_as_view_once(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(view_once=False), owner)

    assert "not confirmed as view-once" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_absent_evidence_fails_closed(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(view_once=None), owner)

    assert "cannot confirm view-once" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_confirmed_view_once_without_current_locator_is_truthfully_unavailable(db_session):
    """Historical transport_available=true must not be treated as a usable locator."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session, transport=True)

    result = await _run(db_session, _event(media_url=None), owner)

    assert "no longer available" in result.reply_text
    for word in ("recovered", "restored", "saved", "stored"):
        assert word not in result.reply_text.lower()
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_untrusted_media_origin_is_refused(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(media_url="https://evil.invalid/steal.jpg"), owner)

    assert "trusted WhatsApp transport" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_deleted_metadata_cannot_be_opened(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session, deleted=True)

    result = await _run(db_session, _event(), owner)

    assert "was deleted" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_mime_and_kind_conflict_produces_no_media_row(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(media_type="video", mimetype="image/png"), owner)

    assert await _outbound(db_session) == []
    assert result.reply_text is not None


# --------------------------------------------------------------------------------------
# Successful OWNER-only return
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("media_type", "mimetype", "url", "expected_kind"),
    [
        ("image", "image/jpeg", "http://waha:3000/api/files/a.jpg", "image"),
        ("video", "video/mp4", "http://waha:3000/api/files/a.mp4", "video"),
        ("ptt", "audio/ogg", "http://waha:3000/api/files/a.ogg", "voice"),
        ("audio", "audio/mpeg", "http://waha:3000/api/files/a.mp3", "audio"),
    ],
)
async def test_available_view_once_media_queues_owner_targeted_row(
    db_session, media_type, mimetype, url, expected_kind
):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(media_type=media_type, mimetype=mimetype, media_url=url), owner)

    rows = await _outbound(db_session)
    assert len(rows) == 1
    row = rows[0]
    # Destination is the OWNER self-DM, never the peer chat the command came from.
    assert row.chat_id == OWNER_ID
    assert row.chat_id != PEER_ID
    assert row.media_type == expected_kind
    assert row.formatting_json["media_mime"] == mimetype
    assert row.formatting_json["source_message_id"] == "SRC-1"
    assert result.outbound_queue_id == row.id


@pytest.mark.asyncio
async def test_queued_return_row_is_bound_and_clears_the_real_delivery_fence(db_session, monkeypatch):
    """The row this command queues must pass the actual P0 owner payload fence.

    `_delivery_authorized` proves the destination is OWNER only after `owner_payload_matches`
    confirms the row's stamp still matches its stored payload. A view-once return that stamped
    itself some other way (or not at all) would be silently refused at delivery time -- a
    regression that would only surface as "OWNER never receives their view-once media", never
    as a failing unit test for this command in isolation.
    """
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_ID)
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    await _run(db_session, _event(), owner)
    rows = await _outbound(db_session)
    assert len(rows) == 1
    row = rows[0]

    authority = OutboundAuthorizationService(db_session)
    allowed, reason, approval_id, authority_type, policy_id = await background_workers._delivery_authorized(db_session, authority, row)
    assert allowed, reason
    assert reason == "exact configured owner chat with bound payload"
    assert approval_id is None
    assert authority_type == "owner_chat"
    assert policy_id is None

    # Mutating the stored locator after the stamp must invalidate the binding, exactly like
    # every other owner producer -- proving this row is bound to the canonical digest and not
    # some other ad-hoc hash.
    row.media_url = "http://waha:3000/api/files/swapped.jpg"
    mutated_allowed, mutated_reason, mutated_approval_id, mutated_authority_type, mutated_policy_id = await background_workers._delivery_authorized(db_session, authority, row)
    assert not mutated_allowed
    assert mutated_reason == "owner queue row payload is not bound to its authorized content"
    assert mutated_approval_id is None
    assert mutated_authority_type is None
    assert mutated_policy_id is None


@pytest.mark.asyncio
async def test_queueing_view_once_return_does_not_claim_delivery(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    await _run(db_session, _event(), owner)

    returned = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert returned is None

    audits = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "view_once_returned_to_owner"))
    ).scalars().all()
    assert audits == []
    assert len(await _outbound(db_session)) == 1


@pytest.mark.asyncio
async def test_repeated_command_message_does_not_queue_two_returns(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    event = _event(command_id="VV-DUP")

    first = await _run(db_session, event, owner)
    second = await _run(db_session, event, owner)

    assert len(await _outbound(db_session)) == 1
    assert first.outbound_queue_id == second.outbound_queue_id


@pytest.mark.asyncio
async def test_no_transport_locator_is_persisted_on_the_queue_row(db_session):
    """The locator is used for delivery but must not leak into stored metadata."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    secret = "http://waha:3000/api/files/SECRET-TOKEN.jpg"

    await _run(db_session, _event(media_url=secret), owner)

    stored = (
        await db_session.execute(text("SELECT * FROM view_once_media_metadata WHERE source_message_id='SRC-1'"))
    ).mappings().first()
    assert "SECRET-TOKEN" not in str(dict(stored))


# --------------------------------------------------------------------------------------
# info / list / delete
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_info_redacts_locator_and_separates_observed_from_current(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(body="@Zina .vv info"), owner, operation="info")

    assert "Retention: OFF" in result.reply_text
    assert "Transport capability when observed" in result.reply_text
    assert "Available now: unknown until you reply" in result.reply_text
    assert "api/files" not in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_list_is_bounded_and_states_position_is_not_an_identifier(db_session):
    owner = await _seed_owner(db_session)
    for index in range(25):
        await _seed_metadata(db_session, source_id=f"SRC-L{index}")

    result = await _run(db_session, _event(quoted_id=None), owner, operation="list")

    numbered = [line for line in result.reply_text.splitlines() if line[:1].isdigit()]
    assert len(numbered) == ViewOnceCommandService.LIST_LIMIT
    assert "list position is not an identifier" in result.reply_text


@pytest.mark.asyncio
async def test_list_reports_nothing_when_no_observations_exist(db_session):
    owner = await _seed_owner(db_session)

    result = await _run(db_session, _event(quoted_id=None), owner, operation="list")

    assert "No view-once media has been observed" in result.reply_text


@pytest.mark.asyncio
async def test_delete_is_truthful_and_durable(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(), owner, operation="delete")

    assert "metadata for this item was deleted" in result.reply_text
    assert "no media bytes were removed" in result.reply_text
    assert "media was deleted" not in result.reply_text

    deleted_at = (
        await db_session.execute(
            text("SELECT deleted_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert deleted_at is not None


@pytest.mark.asyncio
async def test_deleted_record_cannot_be_reopened_after_reload(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner, operation="delete")
    await db_session.commit()

    result = await _run(db_session, _event(command_id="VV-AFTER-DELETE"), owner)

    assert "was deleted" in result.reply_text
    assert await _outbound(db_session) == []


# --------------------------------------------------------------------------------------
# Retention
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retain_off_is_truthful(db_session):
    owner = await _seed_owner(db_session)

    result = await _run(db_session, _event(quoted_id=None), owner, operation="retain_off")

    assert "retention is OFF" in result.reply_text
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_retain_on_remains_unavailable(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(quoted_id=None), owner, operation="retain_on")

    assert "not available yet" in result.reply_text
    assert "Retention is OFF" in result.reply_text

    modes = (
        await db_session.execute(text("SELECT DISTINCT retention_mode FROM view_once_media_metadata"))
    ).scalars().all()
    assert modes == ["none"]



class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ViewOnceWorkerClient:
    def __init__(self, failure=None, on_send=None):
        self.calls = []
        self.failure = failure
        self.on_send = on_send

    async def send_image(self, chat_id, *, media_url, mimetype, caption=None, filename=None):
        self.calls.append((chat_id, media_url, mimetype, caption, filename))
        if self.on_send is not None:
            await self.on_send()
        if self.failure is not None:
            raise self.failure
        return {"id": "mock-view-once-return"}

    async def send_text(self, *, chat_id, text):
        raise AssertionError("view-once return must use the typed image transport")


async def _deliver_view_once(db_session, monkeypatch, client):
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_ID)
    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    return await background_workers._deliver_due_outbound_messages(client)


@pytest.mark.asyncio
async def test_worker_marks_view_once_return_only_after_waha_success(db_session, monkeypatch):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    row = (await _outbound(db_session))[0]

    before = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert before is None

    client = _ViewOnceWorkerClient()
    await _deliver_view_once(db_session, monkeypatch, client)
    await db_session.refresh(row)

    after = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert row.status == "sent"
    assert len(client.calls) == 1
    assert after is not None
    audits = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "view_once_returned_to_owner")
        )
    ).scalars().all()
    assert len(audits) == 1


@pytest.mark.asyncio
async def test_deleted_view_once_source_blocks_pending_owner_return_before_waha(db_session, monkeypatch):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    row = (await _outbound(db_session))[0]

    await _run(db_session, _event(command_id="VV-DEL"), owner, operation="delete")
    client = _ViewOnceWorkerClient()
    await _deliver_view_once(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert client.calls == []
    assert row.status == "deferred"
    assert "deleted" in (row.error_message or "").lower()
    returned = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert returned is None


@pytest.mark.asyncio
async def test_uncertain_view_once_return_does_not_mark_returned_or_retry(db_session, monkeypatch):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    row = (await _outbound(db_session))[0]
    client = _ViewOnceWorkerClient(failure=WahaClientError("connection closed before response"))

    await _deliver_view_once(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert len(client.calls) == 1
    assert row.status == "deferred"
    assert "automatic replay blocked" in (row.error_message or "")
    returned = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert returned is None

    await _deliver_view_once(db_session, monkeypatch, client)
    assert len(client.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value", "expected_reason"),
    [
        ("source_chat_id", "2348000000009@c.us", "source chat"),
        ("command_message_id", "", "command message id"),
    ],
)
async def test_worker_fails_closed_on_invalid_view_once_source_binding(
    db_session, monkeypatch, field, value, expected_reason
):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    row = (await _outbound(db_session))[0]

    metadata = dict(row.formatting_json)
    metadata[field] = value
    row.formatting_json = metadata
    row.formatting_json = OutboundAuthorizationService.stamp_owner_payload(row)
    await db_session.flush()
    assert OutboundAuthorizationService.owner_payload_matches(row)

    client = _ViewOnceWorkerClient()
    await _deliver_view_once(db_session, monkeypatch, client)
    await db_session.refresh(row)

    assert client.calls == []
    assert row.status == "deferred"
    assert expected_reason in (row.error_message or "").lower()


@pytest.mark.asyncio
async def test_worker_holds_view_once_source_lock_through_waha_attempt(db_session, monkeypatch):
    """A concurrent OWNER delete must wait until the single return attempt commits."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    queue = (await _outbound(db_session))[0]
    queue_id = int(queue.id)
    await db_session.commit()

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
    )
    engine = create_async_engine(database_url, pool_size=2)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    send_started = asyncio.Event()
    release_send = asyncio.Event()
    delete_started = asyncio.Event()

    async def pause_transport():
        send_started.set()
        await release_send.wait()

    client = _ViewOnceWorkerClient(on_send=pause_transport)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_ID)
    monkeypatch.setattr(background_workers, "SessionLocal", Session)

    async def delete_source():
        async with Session() as session:
            # Ensure this task owns a database connection before signalling that it is
            # about to issue the UPDATE; the only expected wait is the source-row lock.
            await session.connection()
            delete_started.set()
            await session.execute(
                text(
                    "UPDATE view_once_media_metadata SET deleted_at=now() "
                    "WHERE source_message_id='SRC-1'"
                )
            )
            await session.commit()

    worker_task = asyncio.create_task(background_workers._deliver_due_outbound_messages(client))
    delete_task = None
    try:
        await asyncio.wait_for(send_started.wait(), timeout=5)
        delete_task = asyncio.create_task(delete_source())
        await asyncio.wait_for(delete_started.wait(), timeout=5)
        with pytest.raises(asyncio.TimeoutError):
            await asyncio.wait_for(asyncio.shield(delete_task), timeout=0.1)

        release_send.set()
        assert await asyncio.wait_for(worker_task, timeout=5) == 1
        await asyncio.wait_for(delete_task, timeout=5)

        async with Session() as verify:
            status = (
                await verify.execute(
                    text("SELECT status FROM outbound_queue WHERE id=:queue_id"),
                    {"queue_id": queue_id},
                )
            ).scalar_one()
            returned, deleted = (
                await verify.execute(
                    text(
                        "SELECT returned_to_owner_at, deleted_at "
                        "FROM view_once_media_metadata WHERE source_message_id='SRC-1'"
                    )
                )
            ).one()
        assert client.calls and status == "sent"
        assert returned is not None and deleted is not None
    finally:
        release_send.set()
        if not worker_task.done():
            await worker_task
        if delete_task is not None and not delete_task.done():
            await delete_task
        await engine.dispose()



@pytest.mark.asyncio
async def test_concurrent_duplicate_view_once_command_queues_exactly_one_return(db_session, monkeypatch):
    """Duplicate webhook deliveries serialize before the idempotency lookup."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await db_session.commit()

    original_existing_return = ViewOnceCommandService._existing_return

    async def delayed_existing_return(self, transport_message_id):
        await asyncio.sleep(0.05)
        return await original_existing_return(self, transport_message_id)

    monkeypatch.setattr(ViewOnceCommandService, "_existing_return", delayed_existing_return)

    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
    )
    engine = create_async_engine(database_url, pool_size=2)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    event = _event(command_id="VV-CONCURRENT")

    async def process_duplicate():
        async with Session() as session:
            result = await _run(session, event, owner)
            await session.commit()
            return result.outbound_queue_id

    try:
        queue_ids = await asyncio.gather(process_duplicate(), process_duplicate())
        async with Session() as session:
            rows = (await session.execute(select(OutboundMessage))).scalars().all()
        assert len(rows) == 1
        assert queue_ids == [rows[0].id, rows[0].id]
    finally:
        await engine.dispose()

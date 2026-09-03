"""View-once OWNER authority and the full command -> worker outbound path.

These tests drive the real Command Center dispatch and the real delivery worker. Only
the WAHA transport is replaced. They prove that the view-once handler is not authority:
every queued row still passes the final P0 authorization fence, and any post-authority
mutation results in zero WAHA calls.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, CommandCatalogEntry, OutboundMessage
from app.services.command_control_service import CommandControlService
from app.workers import background_workers

from tests.unit.test_outbound_media_production_path import (
    _RecordingClient,
    _SessionContext,
)


OWNER_ID = "2348000000001@c.us"
PEER_ID = "2348000000002@c.us"
STRANGER_ID = "2348000000009@c.us"
TRUSTED_URL = "http://waha:3000/api/files/vv.jpg"


async def _seed_catalog(db_session):
    db_session.add(
        CommandCatalogEntry(
            name="/vvopen",
            trigger_syntax=".vvopen",
            category="owner",
            description="Open a view-once message privately.",
            example=".vvopen",
            permissions="owner",
            handler_target="command_control:view_once",
            is_enabled=True,
        )
    )
    await db_session.flush()


async def _seed_owner(db_session, *, permission="owner", chat_id=OWNER_ID, primary=True):
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number=chat_id.split("@")[0],
        normalized_whatsapp_id=chat_id,
        role="primary_admin" if primary else "admin",
        permission_level=permission,
        is_primary=primary,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()
    return owner


async def _seed_metadata(db_session, source_id="SRC-1"):
    from sqlalchemy import text

    await db_session.execute(
        text(
            """
            INSERT INTO view_once_media_metadata (
                source_message_id, source_chat_id, media_type, media_mime,
                capability_state, evidence_source, transport_available, retention_mode
            ) VALUES (:sid, :chat, 'image', 'image/jpeg',
                      'transient_available', 'waha_payload', true, 'none')
            """
        ),
        {"sid": source_id, "chat": PEER_ID},
    )


def _event(*, body="@Zina .vvopen", from_me=True, chat_id=PEER_ID, command_id="VV-1", quoted_id="SRC-1"):
    payload = {
        "id": command_id,
        "chatId": chat_id,
        "from": chat_id,
        "fromMe": from_me,
        "body": body,
    }
    if quoted_id:
        payload["replyTo"] = {
            "id": quoted_id,
            "hasMedia": True,
            "isViewOnce": True,
            "media": {"url": TRUSTED_URL, "mimetype": "image/jpeg", "type": "image"},
        }
    return {"event": "message.any", "session": "default", "payload": payload}


async def _dispatch(db_session, event):
    message = MessageNormalizer().normalize(event)
    return await CommandControlService(db_session).handle_from_me(
        message, transport_message_id=event["payload"]["id"]
    )


async def _outbound(db_session):
    return (await db_session.execute(select(OutboundMessage))).scalars().all()


# --------------------------------------------------------------------------------------
# OWNER authorization
# --------------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_owner_is_accepted_and_media_is_queued_to_owner_self_dm(db_session, monkeypatch):
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", OWNER_ID)
    await _seed_catalog(db_session)
    await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _dispatch(db_session, _event())

    assert result is not None and result.consumed
    rows = await _outbound(db_session)
    assert len(rows) == 1
    assert rows[0].chat_id == OWNER_ID


@pytest.mark.asyncio
async def test_non_owner_inbound_message_is_not_a_view_once_command(db_session, monkeypatch):
    """A stranger's inbound `.vvopen` never reaches the OWNER command surface."""
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", OWNER_ID)
    await _seed_catalog(db_session)
    await _seed_owner(db_session)
    await _seed_metadata(db_session)

    from app.api.inbound import _is_from_me

    event = _event(from_me=False, chat_id=STRANGER_ID)
    # The owner command surface is unreachable for a peer-authored message: the
    # ingress gate at inbound.py only calls handle_from_me when fromMe is true.
    assert _is_from_me(event["payload"]) is False
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_admin_without_owner_permission_is_denied(db_session, monkeypatch):
    """ADMIN is not OWNER. A non-owner permission level cannot open view-once media."""
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", "")
    await _seed_catalog(db_session)
    await _seed_owner(db_session, permission="admin")
    await _seed_metadata(db_session)

    result = await _dispatch(db_session, _event())

    # Either an explicit denial or no owner surface at all; both are fail-closed.
    if result is not None:
        assert result.error in {"owner permission required", "command disabled"}
    media_rows = [row for row in await _outbound(db_session) if row.media_url]
    assert media_rows == []


@pytest.mark.asyncio
async def test_primary_owner_lookup_requires_owner_permission(db_session, monkeypatch):
    """ADMIN is not OWNER: a non-owner permission level is never the primary owner."""
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", "")
    await _seed_owner(db_session, permission="admin")

    resolved = await CommandControlService(db_session)._primary_owner()

    assert resolved is None


@pytest.mark.asyncio
async def test_handler_rejects_non_owner_permission_directly(db_session, monkeypatch):
    """Defense in depth: the dispatch guard denies even if a non-owner is passed in."""
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", "")
    await _seed_catalog(db_session)
    await _seed_metadata(db_session)
    admin = await _seed_owner(db_session, permission="admin")

    service = CommandControlService(db_session)
    monkeypatch.setattr(service, "_primary_owner", lambda: _as_owner(admin))

    result = await service.handle_from_me(
        MessageNormalizer().normalize(_event()), transport_message_id="VV-ADMIN"
    )

    assert result is not None
    assert result.error == "owner permission required"
    assert [row for row in await _outbound(db_session) if row.media_url] == []


async def _as_owner(admin):
    return admin


@pytest.mark.asyncio
async def test_spoofed_owner_metadata_cannot_become_owner(db_session, monkeypatch):
    """A peer claiming the owner's display identity is not the configured owner."""
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", OWNER_ID)
    await _seed_catalog(db_session)
    await _seed_owner(db_session)
    await _seed_metadata(db_session)

    from app.api.inbound import _is_from_me

    event = _event(from_me=False, chat_id=STRANGER_ID)
    event["payload"]["_data"] = {"notifyName": "Fabian", "isOwner": True}
    event["payload"]["author"] = OWNER_ID

    # Spoofed display metadata never satisfies the transport-level fromMe gate.
    assert _is_from_me(event["payload"]) is False
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_no_owner_configured_fails_closed(db_session, monkeypatch):
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", "")
    await _seed_catalog(db_session)
    await _seed_metadata(db_session)

    result = await _dispatch(db_session, _event())

    assert result is None
    assert await _outbound(db_session) == []


@pytest.mark.asyncio
async def test_disabled_catalog_entry_blocks_the_command(db_session, monkeypatch):
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", OWNER_ID)
    db_session.add(
        CommandCatalogEntry(
            name="/vvopen",
            trigger_syntax=".vvopen",
            category="owner",
            description="Open a view-once message privately.",
            example=".vvopen",
            permissions="owner",
            handler_target="command_control:view_once",
            is_enabled=False,
        )
    )
    await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _dispatch(db_session, _event())

    assert result.error == "command disabled"
    media_rows = [row for row in await _outbound(db_session) if row.media_url]
    assert media_rows == []


# --------------------------------------------------------------------------------------
# Command -> queue -> final P0 fence -> typed dispatch
# --------------------------------------------------------------------------------------


async def _deliver(db_session, monkeypatch, client):
    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    return await background_workers._deliver_due_outbound_messages(client)


async def _queue_owner_media(db_session, monkeypatch, command_id="VV-1"):
    monkeypatch.setattr("app.services.admin_management_service.settings.owner_whatsapp_ids", OWNER_ID)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", OWNER_ID)
    await _seed_catalog(db_session)
    await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _dispatch(db_session, _event(command_id=command_id))
    await db_session.commit()
    return (
        await db_session.execute(select(OutboundMessage).order_by(OutboundMessage.id.desc()).limit(1))
    ).scalar_one()


@pytest.mark.asyncio
async def test_view_once_media_reaches_typed_image_dispatch(db_session, monkeypatch):
    row = await _queue_owner_media(db_session, monkeypatch)
    client = _RecordingClient()

    await _deliver(db_session, monkeypatch, client)

    assert [call[0] for call in client.calls] == ["send_image"]
    assert client.calls[0][1]["chatId"] == OWNER_ID


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field, value",
    [
        ("chat_id", STRANGER_ID),
        ("media_url", "http://waha:3000/api/files/swapped.jpg"),
        ("media_type", "video"),
        ("media_caption", "attacker caption"),
        ("message_text", "attacker text"),
    ],
)
async def test_mutation_after_authority_results_in_zero_waha_calls(db_session, monkeypatch, field, value):
    """The final fence rejects any row mutated after its authority hash was stamped."""
    row = await _queue_owner_media(db_session, monkeypatch)

    setattr(row, field, value)
    await db_session.commit()

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)

    assert client.calls == []


@pytest.mark.asyncio
async def test_duplicate_command_message_does_not_deliver_twice(db_session, monkeypatch):
    await _queue_owner_media(db_session, monkeypatch, command_id="VV-DUP")
    # Replaying the identical OWNER command message must not create a second return.
    await _dispatch(db_session, _event(command_id="VV-DUP"))
    await db_session.commit()

    media_rows = [row for row in await _outbound(db_session) if row.media_url]
    assert len(media_rows) == 1

    client = _RecordingClient()
    await _deliver(db_session, monkeypatch, client)
    assert len(client.calls) == 1


@pytest.mark.asyncio
async def test_uncertain_send_is_not_blindly_retried(db_session, monkeypatch):
    from app.services.waha_client import WahaClientError

    await _queue_owner_media(db_session, monkeypatch)
    client = _RecordingClient(fail=WahaClientError("timeout"))

    await _deliver(db_session, monkeypatch, client)
    first = len(client.calls)
    await _deliver(db_session, monkeypatch, client)

    assert len(client.calls) == first

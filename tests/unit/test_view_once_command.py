"""OWNER-only view-once command family.

The handler is capability inspection plus queueing, never authority. It makes no WAHA
call, and every row it creates still passes the existing P0 final authorization fence.

Media is returned only when an exact same-source transient capability exists in the
OWNER's own reply payload at command time. A historical observation alone can never
produce a send, because the durable record deliberately stores no locator.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, AuditLog, OutboundMessage, PrivateMediaArtifact
from app.services.command_control_service import CommandControlService
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.private_media_artifact_service import PrivateMediaArtifactResult, PrivateMediaArtifactService
from app.services.view_once_command_service import ViewOnceCommandService
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


async def _seed_metadata(db_session, *, source_id="SRC-1", deleted=False, transport=True, contact_id=None):
    await db_session.execute(
        text(
            """
            INSERT INTO view_once_media_metadata (
                source_message_id, source_chat_id, source_contact_id, media_type, media_mime,
                capability_state, evidence_source, transport_available, retention_mode,
                deleted_at
            ) VALUES (
                :sid, :chat, :contact_id, 'image', 'image/jpeg',
                'transient_available', 'waha_payload', :transport, 'none',
                CASE WHEN :deleted THEN now() ELSE NULL END
            )
            """
        ),
        {"sid": source_id, "chat": PEER_ID, "contact_id": contact_id, "transport": transport, "deleted": deleted},
    )


async def _outbound(db_session):
    return (await db_session.execute(select(OutboundMessage))).scalars().all()


async def _run(db_session, event, owner, operation=None, request_id=None):
    message = _normalize(event)
    command, args = CommandControlService.parse(message.message_text)
    resolved = operation or CommandControlService._view_once_operation(command, args)
    return await ViewOnceCommandService(db_session).handle(
        resolved,
        message=message,
        owner=owner,
        transport_message_id=event["payload"]["id"],
        request_id=request_id,
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
    allowed, reason, _ = await background_workers._delivery_authorized(db_session, authority, row)
    assert allowed, reason
    assert reason == "exact configured owner chat with bound payload"

    # Mutating the stored locator after the stamp must invalidate the binding, exactly like
    # every other owner producer -- proving this row is bound to the canonical digest and not
    # some other ad-hoc hash.
    row.media_url = "http://waha:3000/api/files/swapped.jpg"
    mutated_allowed, mutated_reason, _ = await background_workers._delivery_authorized(db_session, authority, row)
    assert not mutated_allowed
    assert mutated_reason == "owner queue row payload is not bound to its authorized content"


@pytest.mark.asyncio
async def test_return_marks_metadata_and_writes_audit(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    await _run(db_session, _event(), owner)

    returned = (
        await db_session.execute(
            text("SELECT returned_to_owner_at FROM view_once_media_metadata WHERE source_message_id='SRC-1'")
        )
    ).scalar_one()
    assert returned is not None

    audits = (
        await db_session.execute(select(AuditLog).where(AuditLog.action == "view_once_returned_to_owner"))
    ).scalars().all()
    assert len(audits) == 1


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
async def test_open_records_metadata_only_provenance_bound_to_owner(db_session):
    """A successful `.vvopen` return also records a PrivateMediaArtifact (roadmap phase 5).

    This is provenance, not authority: no bytes, no storage_locator, and it must be
    associated with the exact OWNER account that received the return.
    """
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    await _run(db_session, _event(), owner)

    artifacts = (await db_session.execute(select(PrivateMediaArtifact))).scalars().all()
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact.source_message_id == "SRC-1"
    # Source identity is where the media originated (the peer chat the quoted message
    # came from), never the OWNER self-DM destination the return is queued to.
    assert artifact.source_chat_id == PEER_ID
    assert artifact.transport_provenance == "view_once_command"
    assert artifact.owner_admin_account_id == owner.id
    assert artifact.media_kind == "image"
    assert artifact.media_mime == "image/jpeg"
    assert artifact.storage_locator is None
    assert artifact.retention_policy == "none"


@pytest.mark.asyncio
async def test_open_passes_request_id_and_verified_byte_size_to_the_artifact(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    event = _event()
    event["payload"]["replyTo"]["media"]["fileSize"] = 12345

    await _run(db_session, event, owner, request_id="req-123")

    artifact = (await db_session.execute(select(PrivateMediaArtifact))).scalars().one()
    assert artifact.byte_size == 12345

    audit = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "private_media_artifact_created")
        )
    ).scalars().one()
    assert audit.details_json["request_id"] == "req-123"


@pytest.mark.asyncio
async def test_open_carries_the_source_contact_into_the_artifact(db_session, test_contact):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session, contact_id=test_contact.id)

    await _run(db_session, _event(), owner)

    artifact = (await db_session.execute(select(PrivateMediaArtifact))).scalars().one()
    assert artifact.source_contact_id == test_contact.id


@pytest.mark.asyncio
async def test_open_logs_a_rejected_artifact_write_instead_of_dropping_it(db_session, monkeypatch, caplog):
    """A validation rejection (`ok=False`, no exception) must still be surfaced.

    The SAVEPOINT exits normally on a clean rejection, so only checking for an
    exception would silently drop the warning -- and, unlike the ingress path, the
    owner return itself must still succeed regardless.
    """
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    async def _rejected(*args, **kwargs):
        return PrivateMediaArtifactResult(False, error="simulated validation rejection")

    monkeypatch.setattr(PrivateMediaArtifactService, "get_or_create_from_observation", _rejected)

    with caplog.at_level("WARNING"):
        result = await _run(db_session, _event(), owner)

    assert result.outbound_queue_id is not None
    assert (await db_session.execute(select(PrivateMediaArtifact))).scalars().all() == []
    assert "private_media_artifact_observation_failed" in caplog.text
    assert "simulated validation rejection" in caplog.text


@pytest.mark.asyncio
async def test_delete_then_reobserve_at_ingress_does_not_resurrect_the_artifact(db_session):
    """The exact regression a create-on-tombstone branch would cause.

    `view_once_media_metadata`'s own upsert is a no-op once a row is deleted (its
    ON CONFLICT ... DO UPDATE is gated on `deleted_at IS NULL`), so ingress observation
    reaches PrivateMediaArtifactService unconditionally on a repeat delivery -- a webhook
    retry replaying the same source after an OWNER `.vv delete` must not recreate an
    active artifact behind their back.
    """
    from app.services.view_once_observation_service import ViewOnceObservationService

    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(command_id="VV-A"), owner)
    artifact_id = (await db_session.execute(select(PrivateMediaArtifact))).scalars().one().artifact_id

    await _run(db_session, _event(command_id="VV-DEL"), owner, operation="delete")
    assert (await db_session.execute(select(PrivateMediaArtifact))).scalars().one().deleted_at is not None

    await ViewOnceObservationService(db_session).observe(
        payload={"id": "SRC-1", "chatId": PEER_ID, "isViewOnce": True, "media": {"url": "http://x/a.jpg", "type": "image"}},
        source_message_id="SRC-1",
        source_chat_id=PEER_ID,
        source_contact_id=None,
    )

    artifacts = (await db_session.execute(select(PrivateMediaArtifact))).scalars().all()
    assert len(artifacts) == 1
    assert artifacts[0].artifact_id == artifact_id
    assert artifacts[0].deleted_at is not None


@pytest.mark.asyncio
async def test_repeated_open_of_the_same_source_does_not_duplicate_the_artifact(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    await _run(db_session, _event(command_id="VV-A"), owner)
    await _run(db_session, _event(command_id="VV-B"), owner)

    artifacts = (await db_session.execute(select(PrivateMediaArtifact))).scalars().all()
    assert len(artifacts) == 1


@pytest.mark.asyncio
async def test_ingress_observed_artifact_and_later_open_converge_on_one_row(db_session):
    """The exact regression a mismatched source_chat_id would cause.

    Ingress records the artifact under the peer chat the message actually came from.
    A later `.vvopen` for the same source must backfill that same row, never mint a
    second one addressed to the OWNER self-DM instead.
    """
    from app.services.view_once_observation_service import ViewOnceObservationService

    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await ViewOnceObservationService(db_session).observe(
        payload={"id": "SRC-1", "chatId": PEER_ID, "isViewOnce": True, "media": {"url": "http://x/a.jpg", "type": "image"}},
        source_message_id="SRC-1",
        source_chat_id=PEER_ID,
        source_contact_id=None,
    )
    assert len((await db_session.execute(select(PrivateMediaArtifact))).scalars().all()) == 1

    await _run(db_session, _event(), owner)

    artifacts = (await db_session.execute(select(PrivateMediaArtifact))).scalars().all()
    assert len(artifacts) == 1
    assert artifacts[0].owner_admin_account_id == owner.id


@pytest.mark.asyncio
async def test_delete_also_tombstones_the_matching_artifact(db_session):
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)
    await _run(db_session, _event(), owner)
    assert (await db_session.execute(select(PrivateMediaArtifact))).scalars().one().deleted_at is None

    await _run(db_session, _event(), owner, operation="delete")

    artifact = (await db_session.execute(select(PrivateMediaArtifact))).scalars().one()
    assert artifact.deleted_at is not None


@pytest.mark.asyncio
async def test_delete_without_a_recorded_artifact_still_succeeds(db_session):
    """`.vv delete` must work even when observation never created an artifact row."""
    owner = await _seed_owner(db_session)
    await _seed_metadata(db_session)

    result = await _run(db_session, _event(), owner, operation="delete")

    assert "was deleted" in result.reply_text
    assert (await db_session.execute(select(PrivateMediaArtifact))).scalars().all() == []


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

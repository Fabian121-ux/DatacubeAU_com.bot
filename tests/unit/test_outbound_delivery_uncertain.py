from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.router import InboundRouter
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, Contact, ContactMessagingConsent, ContactMessagingConsentEvent, Message, OutboundMessage
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
from app.services.inbound_idempotency_service import InboundIdempotencyService, InboundReceipt
from app.services.outbound_authorization_service import AuthorizationDecision, OutboundAuthorizationService
from app.services.outbound_safety_limit_service import OutboundSafetyDecision
from app.services.scheduled_action_service import ScheduledActionService
from app.services.waha_client import WahaClientError
from app.utils.time import utcnow
from app.workers import background_workers


class _SessionContext:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _ExplodingClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise AssertionError("stale sending row must never be replayed")


class _UncertainClient:
    def __init__(self):
        self.calls = 0

    async def send_text(self, *, chat_id, text):
        self.calls += 1
        raise WahaClientError("connection closed before response")

    async def send_media(self, **kwargs):
        self.calls += 1
        raise WahaClientError("connection closed before response")


class _RecordingClient:
    def __init__(self):
        self.calls: list[tuple[str, str]] = []

    async def send_text(self, *, chat_id, text):
        self.calls.append((chat_id, text))
        return {"id": "mock-waha-message-id"}

    async def send_media(self, **kwargs):
        raise AssertionError("formatted text regression must use the text send path")


@pytest.mark.asyncio
async def test_stale_sending_row_is_quarantined_without_waha_replay(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="already attempted",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(row)
    await db_session.commit()
    row_id = row.id

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    client = _ExplodingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 0
    assert client.calls == 0
    assert row.id == row_id
    assert row.status == "deferred"
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_waha_send_error_is_delivery_uncertain_not_retrying(db_session, monkeypatch):
    now = utcnow()
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="attempt once",
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.flush()
    row.formatting_json = OutboundAuthorizationService.stamp_owner_payload(row)
    await db_session.commit()

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    # This test isolates the post-authorization uncertain-send state machine. Make the
    # exact target the configured OWNER self-DM so the final authorization fence is
    # explicitly satisfied without weakening the external-contact fail-closed path.
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "222@c.us")
    client = _UncertainClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == 1
    assert row.status == "deferred"
    assert row.retry_count == 0
    assert "automatic replay blocked" in (row.error_message or "")


@pytest.mark.asyncio
async def test_authorized_external_worker_preserves_whatsapp_formatting_exactly(db_session, test_contact, monkeypatch):
    now = utcnow()
    text = "> quoted line\n\n*Important* uses `inline code`.\n\nFinal paragraph."
    # This regression now uses real durable source/contact rows and explicit consent;
    # the worker must not treat mocked authority as a substitute for consent state.
    test_contact.whatsapp_id = "222@c.us"
    test_contact.chat_id = "222@c.us"
    inbound = Message(
        contact_id=test_contact.id,
        chat_id="222@c.us",
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(inbound)
    await db_session.flush()
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id="222@c.us",
        evidence_ref="owner-attested-2026-10-24",
        owner_identity="OWNER",
    )
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": inbound.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    await db_session.commit()

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        return context, AuthorizationDecision(True, "contact_policy", "exact active contact policy")

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == [("222@c.us", text)]
    assert row.message_text == text
    assert row.status == "sent"


@pytest.mark.parametrize(
    ("authority_type", "approval_id", "consent_state"),
    [
        ("contact_policy", None, "unknown"),
        ("one_use_approval", 123, "unknown"),
        ("contact_policy", None, "opted_out"),
        ("one_use_approval", 123, "opted_out"),
    ],
)
@pytest.mark.asyncio
async def test_external_contact_consent_is_required_even_when_authority_allows(
    db_session, test_contact, monkeypatch, authority_type, approval_id, consent_state
):
    now = utcnow()
    test_contact.whatsapp_id = "222@c.us"
    test_contact.chat_id = "222@c.us"
    inbound = Message(
        contact_id=test_contact.id,
        chat_id="222@c.us",
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(inbound)
    await db_session.flush()

    text = "reply without explicit consent"
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text=text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": inbound.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(row)
    if consent_state == "opted_out":
        await ContactMessagingConsentService(db_session).record_inbound_opt_out(
            contact_id=test_contact.id,
            exact_chat_id="222@c.us",
            evidence_ref="inbound-stop-test",
        )
    await db_session.commit()

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        # Neither a live contact policy nor a one-use approval may bypass the final
        # exact-contact consent fence. This is intentionally mocked as already allowed.
        return context, AuthorizationDecision(
            True, authority_type, f"active {authority_type}", approval_id=approval_id
        )

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(row)
    assert processed == 1
    assert client.calls == []
    assert row.status == "deferred"
    assert "contact consent denied" in (row.error_message or "")
    expected_consent_reason = "unknown" if consent_state == "unknown" else "opted out"
    assert expected_consent_reason in (row.error_message or "")


@pytest.mark.asyncio
async def test_delivery_uncertain_state_survives_restart_style_reload(db_session):
    row = OutboundMessage(
        chat_id="222@c.us",
        message_text="uncertain",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=utcnow(),
        updated_at=utcnow(),
    )
    db_session.add(row)
    await db_session.flush()
    row_id = row.id

    await background_workers._mark_delivery_uncertain(
        db_session,
        row,
        reason="delivery outcome uncertain; automatic replay blocked",
    )
    db_session.expire_all()

    persisted = await db_session.get(OutboundMessage, row_id)
    assert persisted is not None
    assert persisted.status == "deferred"
    assert "automatic replay blocked" in (persisted.error_message or "")


@pytest.mark.asyncio
async def test_uncertain_scheduled_action_cannot_be_rereleased_or_replayed_after_restart(db_session, monkeypatch):
    now = utcnow()
    outbound = OutboundMessage(
        chat_id="333@c.us",
        message_text="owner scheduled exact text",
        status="sending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(outbound)
    await db_session.flush()

    action = ScheduledAction(
        action_type="whatsapp.send_message",
        target_contact_id=None,
        target_chat_id="333@c.us",
        payload_json={"text": "owner scheduled exact text"},
        timezone="UTC",
        scheduled_for=now - timedelta(minutes=20),
        status="queued",
        is_enabled=True,
        retry_count=0,
        max_retries=3,
        outbound_queue_id=outbound.id,
        idempotency_key="test-uncertain-scheduled-action-no-replay",
        metadata_json={},
        executed_at=now - timedelta(minutes=10),
        updated_at=now - timedelta(minutes=10),
    )
    db_session.add(action)
    await db_session.flush()
    outbound.formatting_json = {"scheduled_action_id": action.id}
    await db_session.commit()

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    client = _ExplodingClient()

    first_processed = await background_workers._deliver_due_outbound_messages(client)
    await db_session.refresh(outbound)
    await db_session.refresh(action)

    assert first_processed == 0
    assert client.calls == 0
    assert outbound.status == "deferred"
    assert action.status == "queued"
    assert action.outbound_queue_id == outbound.id
    assert (action.metadata_json or {}).get("delivery", {}).get("status") == "deferred"

    outbound_id = outbound.id
    action_id = action.id
    db_session.expire_all()
    release_count = await ScheduledActionService(db_session).release_due(limit=25)
    await db_session.commit()
    second_processed = await background_workers._deliver_due_outbound_messages(client)

    persisted_outbound = await db_session.get(OutboundMessage, outbound_id)
    persisted_action = await db_session.get(ScheduledAction, action_id)
    assert release_count == 0
    assert second_processed == 0
    assert client.calls == 0
    assert persisted_outbound is not None and persisted_outbound.status == "deferred"
    assert persisted_action is not None and persisted_action.status == "queued"
    assert persisted_action.outbound_queue_id == persisted_outbound.id


@pytest.mark.asyncio
@pytest.mark.parametrize("source_kind", ["inbound", "scheduled"])
async def test_contact_remap_after_queue_creation_blocks_external_dispatch(
    db_session, test_contact, monkeypatch, source_kind
):
    """A historical source must not authorize an old chat after Contact remapping."""
    now = utcnow()
    old_chat = "222@c.us"
    new_chat = "333@c.us"
    text = "must not reach a stale destination"
    test_contact.whatsapp_id = old_chat
    test_contact.chat_id = old_chat
    await db_session.flush()

    metadata = {
        "delivery_policy": "approval_required",
        "content_sha256": OutboundAuthorizationService.content_hash(text),
        "response_category": "normal_reply",
    }
    if source_kind == "inbound":
        inbound = Message(
            contact_id=test_contact.id,
            chat_id=old_chat,
            chat_type="dm",
            direction="inbound",
            message_text="original inbound",
            normalized_text="original inbound",
            message_type="text",
        )
        db_session.add(inbound)
        await db_session.flush()
        metadata.update({
            "inbound_message_id": inbound.id,
            "contact_id": test_contact.id,
        })

    queue = OutboundMessage(
        chat_id=old_chat,
        message_text=text,
        formatting_json=metadata,
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.flush()

    if source_kind == "scheduled":
        action = ScheduledAction(
            action_type="whatsapp.send_message",
            target_contact_id=test_contact.id,
            target_chat_id=old_chat,
            payload_json={"text": text},
            timezone="UTC",
            scheduled_for=now - timedelta(minutes=1),
            status="queued",
            is_enabled=True,
            retry_count=0,
            max_retries=3,
            outbound_queue_id=queue.id,
            idempotency_key=f"test-contact-remap-{source_kind}-{test_contact.id}",
            metadata_json={},
        )
        db_session.add(action)
        await db_session.flush()
        queue.formatting_json = {"scheduled_action_id": action.id}

    # Consent is valid for the old destination at queue creation time.
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=old_chat,
        evidence_ref=f"owner-remap-{source_kind}",
        owner_identity="OWNER",
    )
    # The Contact is then remapped before the final worker fence executes.
    test_contact.whatsapp_id = new_chat
    test_contact.chat_id = new_chat
    await db_session.commit()

    async def _authorized(session, authority, message):
        return True, "test authority permits this row", None

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(background_workers, "SessionLocal", lambda: _SessionContext(db_session))
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    monkeypatch.setattr(background_workers, "_delivery_authorized", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)
    client = _RecordingClient()

    processed = await background_workers._deliver_due_outbound_messages(client)

    await db_session.refresh(queue)
    assert processed == 1
    assert client.calls == []
    assert queue.status == "deferred"
    assert "current contact/chat mapping does not match recipient" in (queue.error_message or "")

@pytest.mark.asyncio
@pytest.mark.parametrize("stop_alias", ["222@c.us", "unmapped-lid-987@lid"])
async def test_claimed_stop_vetoes_send_before_routing_can_apply_consent(
    db_session, test_contact, monkeypatch, stop_alias
):
    now = utcnow()
    test_contact.whatsapp_id = "222@c.us"
    test_contact.chat_id = "222@c.us"
    await db_session.flush()
    source = Message(
        contact_id=test_contact.id,
        chat_id="222@c.us",
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(source)
    await db_session.flush()
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id="222@c.us",
        evidence_ref="owner-attested-stop-race",
        owner_identity="OWNER",
    )
    reply_text = "previously consented reply"
    queue = OutboundMessage(
        chat_id="222@c.us",
        message_text=reply_text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": source.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(reply_text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.commit()
    queue_id = int(queue.id)
    contact_id = int(test_contact.id)

    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", factory)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        return context, AuthorizationDecision(True, "contact_policy", "current contact policy")

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)

    at_final_veto = asyncio.Event()
    resume_dispatch = asyncio.Event()
    original_pending_check = ContactMessagingConsentService.has_pending_opt_out_intent_for_contact

    async def pause_at_final_veto(service, locked_contact_id):
        at_final_veto.set()
        await resume_dispatch.wait()
        return await original_pending_check(service, locked_contact_id)

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "has_pending_opt_out_intent_for_contact",
        pause_at_final_veto,
    )
    client = _RecordingClient()
    worker_task = asyncio.create_task(background_workers._deliver_due_outbound_messages(client))
    await asyncio.wait_for(at_final_veto.wait(), timeout=5)

    event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": "STOP-RACE-1",
            "chatId": stop_alias,
            "from": stop_alias,
            "senderId": "222@c.us",
            "fromMe": False,
            "body": "STOP",
        },
    }
    event_key = f"test:{stop_alias}:STOP-RACE-1"

    # Model the real ingress sequence in one task: claim commits the STOP receipt
    # before waiting for the worker's mapping/Contact lock, then routing applies the
    # opt-out and completes the same lease after the worker releases that boundary.
    async def route_stop():
        async with factory() as route_session:
            idempotency = InboundIdempotencyService(route_session)
            claimed = await idempotency.claim(
                InboundReceipt(
                    event_key=event_key,
                    session_name="test",
                    chat_id=stop_alias,
                    message_id="STOP-RACE-1",
                    sender_identity_ids=("222@c.us", stop_alias),
                    sender_contact_ids=(str(contact_id),),
                    opt_out_intent=True,
                )
            )
            assert claimed is True
            result = await InboundRouter(route_session).process_event(event)
            await idempotency.mark_completed(event_key)
            return result

    route_task = asyncio.create_task(route_stop())

    # Do not await claim() directly: after committing the receipt, production claim()
    # intentionally waits for the dispatch boundary. Observe the committed veto from
    # a third session while routing is blocked, then let the worker reach its final check.
    async def wait_for_committed_stop_receipt():
        for _ in range(100):
            if route_task.done():
                await route_task
                raise AssertionError("STOP routing finished before the worker released its boundary")
            async with factory() as observer_session:
                receipt = (
                    await observer_session.execute(
                        text(
                            "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                            "WHERE event_key = :event_key"
                        ),
                        {"event_key": event_key},
                    )
                ).one_or_none()
                if receipt is not None and receipt.opt_out_intent is True and receipt.status == "processing":
                    observer_consent = ContactMessagingConsentService(observer_session)
                    if stop_alias == "222@c.us":
                        assert await observer_consent.has_pending_opt_out_intent("222@c.us") is True
                    else:
                        assert await original_pending_check(observer_consent, contact_id) is True
                    return
            await asyncio.sleep(0.01)
        raise AssertionError("committed pending STOP receipt was not visible within 1 second")

    await asyncio.wait_for(wait_for_committed_stop_receipt(), timeout=5)
    assert not route_task.done(), "routing must still be waiting on the worker's dispatch boundary"

    resume_dispatch.set()
    processed = await asyncio.wait_for(worker_task, timeout=5)
    route_result = await asyncio.wait_for(route_task, timeout=5)

    assert processed == 1
    assert client.calls == []
    assert route_result["action"] == "ignored"
    await db_session.refresh(queue)
    assert queue.status == "deferred"
    assert "pending inbound opt-out intent" in (queue.error_message or "")

    async with factory() as verify_session:
        consent = (
            await verify_session.execute(
                select(ContactMessagingConsent)
                .where(ContactMessagingConsent.contact_id == contact_id)
                .where(ContactMessagingConsent.exact_chat_id == stop_alias)
            )
        ).scalar_one()
        assert consent.status == "opted_out"

        events = (
            await verify_session.execute(
                select(ContactMessagingConsentEvent)
                .where(ContactMessagingConsentEvent.contact_id == contact_id)
                .where(ContactMessagingConsentEvent.exact_chat_id == stop_alias)
            )
        ).scalars().all()
        assert any(row.event_type == "opted_out" for row in events)

        audits = (
            await verify_session.execute(
                select(AuditLog).where(AuditLog.action == "contact_messaging_consent_changed")
            )
        ).scalars().all()
        assert any(
            row.details_json.get("exact_chat_id") == stop_alias
            and row.details_json.get("status") == "opted_out"
            for row in audits
        )

        receipt = (
            await verify_session.execute(
                text(
                    "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                    "WHERE event_key = :event_key"
                ),
                {"event_key": event_key},
            )
        ).one()
        assert receipt.opt_out_intent is True
        assert receipt.status == "completed"


@pytest.mark.asyncio
async def test_pending_stop_on_mapped_alias_blocks_queued_other_alias(
    db_session, test_contact, monkeypatch
):
    now = utcnow()
    target_chat_id = "222@c.us"
    opt_out_alias = "333@c.us"
    test_contact.whatsapp_id = target_chat_id
    test_contact.chat_id = opt_out_alias
    await db_session.flush()

    source = Message(
        contact_id=test_contact.id,
        chat_id=target_chat_id,
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(source)
    await db_session.flush()
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=target_chat_id,
        evidence_ref="owner-attested-alias-stop-race",
        owner_identity="OWNER",
    )
    reply_text = "must be vetoed by STOP on the mapped alias"
    queue = OutboundMessage(
        chat_id=target_chat_id,
        message_text=reply_text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": source.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(reply_text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.commit()
    queue_id = int(queue.id)
    contact_id = int(test_contact.id)

    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", factory)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        return context, AuthorizationDecision(True, "contact_policy", "current contact policy")

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)

    at_final_veto = asyncio.Event()
    resume_dispatch = asyncio.Event()
    original_pending_check = ContactMessagingConsentService.has_pending_opt_out_intent_for_contact

    async def pause_at_final_veto(service, checked_contact_id):
        at_final_veto.set()
        await resume_dispatch.wait()
        return await original_pending_check(service, checked_contact_id)

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "has_pending_opt_out_intent_for_contact",
        pause_at_final_veto,
    )
    client = _RecordingClient()
    worker_task = asyncio.create_task(background_workers._deliver_due_outbound_messages(client))
    await asyncio.wait_for(at_final_veto.wait(), timeout=5)

    event_key = "test:333@c.us:STOP-ALIAS-RACE-1"

    async def claim_stop():
        async with factory() as receipt_session:
            return await InboundIdempotencyService(receipt_session).claim(
                InboundReceipt(
                    event_key=event_key,
                    session_name="test",
                    chat_id=opt_out_alias,
                    message_id="STOP-ALIAS-RACE-1",
                    opt_out_intent=True,
                )
            )

    # claim() commits the STOP receipt before it waits for the Contact/mapping
    # lock held by the paused dispatch worker. Awaiting claim() here would invert
    # the test's own release order and deadlock: the worker cannot inspect the
    # committed receipt until resume_dispatch is set.
    claim_task = asyncio.create_task(claim_stop())
    worker_result = claim_result = None
    try:
        async with factory() as observer_session:
            for _ in range(100):
                receipt = (
                    await observer_session.execute(
                        text(
                            "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                            "WHERE event_key = :event_key"
                        ),
                        {"event_key": event_key},
                    )
                ).one_or_none()
                if receipt is not None and receipt.opt_out_intent is True:
                    assert receipt.status == "processing"
                    # This method is monkeypatched to pause the worker. Use the saved
                    # original for the observer, or the observer would wait on the same
                    # release event and deadlock the test before it can release the worker.
                    assert await original_pending_check(
                        ContactMessagingConsentService(observer_session), contact_id
                    ) is True
                    break
                await asyncio.sleep(0.01)
            else:
                pytest.fail("STOP receipt was not committed before the dispatch fence timeout")

        assert not claim_task.done(), (
            "STOP claim should wait on the Contact lock only after its receipt is visible"
        )
    finally:
        # Always release the paused worker and drain both tasks, even if an
        # assertion fails, so this regression cannot strand the PostgreSQL test suite.
        resume_dispatch.set()
        worker_result, claim_result = await asyncio.wait_for(
            asyncio.gather(worker_task, claim_task, return_exceptions=True),
            timeout=10,
        )

    assert not isinstance(worker_result, BaseException), repr(worker_result)
    assert not isinstance(claim_result, BaseException), repr(claim_result)
    assert claim_result is True
    assert worker_result == 1
    assert client.calls == []
    await db_session.refresh(queue)
    assert queue.status == "deferred"
    assert "pending inbound opt-out intent" in (queue.error_message or "")

    async with factory() as verify_session:
        receipt = (
            await verify_session.execute(
                text(
                    "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                    "WHERE event_key = :event_key"
                ),
                {"event_key": event_key},
            )
        ).one()
        assert receipt.opt_out_intent is True
        assert receipt.status == "processing"


@pytest.mark.asyncio
@pytest.mark.parametrize("uncertain", [False, True])
async def test_stop_after_dispatch_reservation_allows_one_attempt_and_blocks_followups(
    db_session, test_contact, monkeypatch, uncertain
):
    """A STOP after the final veto read cannot cancel the reserved attempt, but vetoes later rows."""
    now = utcnow()
    chat_id = "222@c.us"
    test_contact.whatsapp_id = chat_id
    test_contact.chat_id = chat_id
    await db_session.flush()

    source = Message(
        contact_id=test_contact.id,
        chat_id=chat_id,
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(source)
    await db_session.flush()
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=chat_id,
        evidence_ref="owner-attested-reserved-send",
        owner_identity="OWNER",
    )

    reply_text = "one attempt already reserved"
    queue = OutboundMessage(
        chat_id=chat_id,
        message_text=reply_text,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": source.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(reply_text),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.commit()

    contact_id = int(test_contact.id)
    queue_id = int(queue.id)
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", factory)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")

    async def _authorized(self, message):
        context = self.context_from_queue_message(message)
        assert context is not None
        return context, AuthorizationDecision(True, "contact_policy", "current contact policy")

    async def _safe(self, message, *, now=None):
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(OutboundAuthorizationService, "authorize_queue_message", _authorized)
    monkeypatch.setattr(background_workers.OutboundSafetyLimitService, "authorize", _safe)

    reservation_reached = asyncio.Event()
    release_reserved_attempt = asyncio.Event()
    original_pending_check = ContactMessagingConsentService.has_pending_opt_out_intent_for_contact

    async def pause_after_final_veto_read(service, locked_contact_id):
        pending = await original_pending_check(service, locked_contact_id)
        assert pending is False, "the reservation boundary must be reached with no prior STOP"
        reservation_reached.set()
        await release_reserved_attempt.wait()
        return pending

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "has_pending_opt_out_intent_for_contact",
        pause_after_final_veto_read,
    )
    client = _UncertainClient() if uncertain else _RecordingClient()
    worker_task = asyncio.create_task(background_workers._deliver_due_outbound_messages(client))
    route_task = None

    event = {
        "event": "message",
        "session": "test",
        "payload": {
            "id": f"STOP-RESERVED-{contact_id}",
            "chatId": chat_id,
            "from": chat_id,
            "senderId": chat_id,
            "fromMe": False,
            "body": "STOP",
        },
    }
    event_key = f"test:{chat_id}:STOP-RESERVED-{contact_id}"

    async def route_stop():
        async with factory() as route_session:
            idempotency = InboundIdempotencyService(route_session)
            claimed = await idempotency.claim(
                InboundReceipt(
                    event_key=event_key,
                    session_name="test",
                    chat_id=chat_id,
                    message_id=f"STOP-RESERVED-{contact_id}",
                    sender_identity_ids=(chat_id,),
                    sender_contact_ids=(str(contact_id),),
                    opt_out_intent=True,
                )
            )
            assert claimed is True
            result = await InboundRouter(route_session).process_event(event)
            await idempotency.mark_completed(event_key)
            return result

    try:
        await asyncio.wait_for(reservation_reached.wait(), timeout=5)
        route_task = asyncio.create_task(route_stop())

        # The receipt must commit while STOP waits behind the worker's already-won
        # transaction-scoped reservation lock. This proves the ordering, not delivery.
        async def wait_for_committed_receipt():
            for _ in range(100):
                if route_task.done():
                    await route_task
                    raise AssertionError("STOP routing completed before the reserved attempt released its lock")
                async with factory() as observer:
                    receipt = (
                        await observer.execute(
                            text(
                                "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                                "WHERE event_key = :event_key"
                            ),
                            {"event_key": event_key},
                        )
                    ).one_or_none()
                    if receipt is not None:
                        assert receipt.opt_out_intent is True
                        assert receipt.status == "processing"
                        return
                await asyncio.sleep(0.01)
            raise AssertionError("STOP receipt did not commit while waiting on the reservation lock")

        await asyncio.wait_for(wait_for_committed_receipt(), timeout=5)
        assert not route_task.done(), "STOP must wait for the already-reserved attempt outcome"
    finally:
        release_reserved_attempt.set()
        tasks = [worker_task]
        if route_task is not None:
            tasks.append(route_task)
        results = await asyncio.wait_for(
            asyncio.gather(*tasks, return_exceptions=True),
            timeout=15,
        )

    assert not isinstance(results[0], BaseException), repr(results[0])
    assert results[0] == 1
    if route_task is not None:
        assert len(results) == 2
        assert not isinstance(results[1], BaseException), repr(results[1])
        assert results[1]["action"] == "ignored"

    await db_session.refresh(queue)
    if uncertain:
        assert isinstance(client, _UncertainClient)
        assert client.calls == 1
        assert queue.status == "deferred"
        assert queue.retry_count == 0
        assert "automatic replay blocked" in (queue.error_message or "")
    else:
        assert isinstance(client, _RecordingClient)
        assert client.calls == [(chat_id, reply_text)]
        assert queue.status == "sent"

    async with factory() as verify_session:
        consent = (
            await verify_session.execute(
                select(ContactMessagingConsent)
                .where(ContactMessagingConsent.contact_id == contact_id)
                .where(ContactMessagingConsent.exact_chat_id == chat_id)
            )
        ).scalar_one()
        assert consent.status == "opted_out"
        receipt = (
            await verify_session.execute(
                text(
                    "SELECT opt_out_intent, status FROM inbound_webhook_receipts "
                    "WHERE event_key = :event_key"
                ),
                {"event_key": event_key},
            )
        ).one()
        assert receipt.opt_out_intent is True
        assert receipt.status == "completed"

    # A later worker pass must not replay an uncertain first attempt.
    assert await background_workers._deliver_due_outbound_messages(client) == 0
    assert client.calls == (1 if uncertain else [(chat_id, reply_text)])

    # A distinct later queue row is still denied by the now-terminal contact opt-out.
    later_text = "must be blocked after STOP completes"
    async with factory() as insert_session:
        later_queue = OutboundMessage(
            chat_id=chat_id,
            message_text=later_text,
            formatting_json={
                "delivery_policy": "approval_required",
                "inbound_message_id": source.id,
                "contact_id": contact_id,
                "content_sha256": OutboundAuthorizationService.content_hash(later_text),
                "response_category": "normal_reply",
            },
            status="pending",
            retry_count=0,
            max_retries=3,
            next_attempt_at=utcnow() - timedelta(seconds=1),
            updated_at=utcnow() - timedelta(seconds=1),
        )
        insert_session.add(later_queue)
        await insert_session.commit()
        later_queue_id = int(later_queue.id)

    assert await background_workers._deliver_due_outbound_messages(client) == 1
    assert client.calls == (1 if uncertain else [(chat_id, reply_text)])
    async with factory() as verify_session:
        later_queue = (
            await verify_session.execute(
                select(OutboundMessage).where(OutboundMessage.id == later_queue_id)
            )
        ).scalar_one()
        assert later_queue.status == "deferred"
        assert "contact consent denied" in (later_queue.error_message or "")

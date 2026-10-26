import asyncio
from datetime import timedelta
from types import SimpleNamespace

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.router import InboundRouter
from app.models.schema import (
    Contact,
    ContactMessagingConsent,
    ContactMessagingConsentEvent,
    Message,
    OutboundMessage,
)
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
from app.utils.time import utcnow


def _inbound(contact, chat_id: str) -> Message:
    return Message(
        contact_id=contact.id,
        chat_id=chat_id,
        chat_type="dm",
        direction="inbound",
        message_text="hello",
        normalized_text="hello",
        message_type="text",
    )


async def _queue_with_source(db_session, contact, chat_id: str) -> OutboundMessage:
    inbound = _inbound(contact, chat_id)
    db_session.add(inbound)
    await db_session.flush()
    queue = OutboundMessage(
        chat_id=chat_id,
        message_text="reply",
        formatting_json={
            "inbound_message_id": inbound.id,
            "contact_id": contact.id,
            "delivery_policy": "approval_required",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(queue)
    await db_session.flush()
    return queue


@pytest.mark.asyncio
async def test_missing_consent_materializes_unknown_and_denies_exact_queue(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)

    decision = await ContactMessagingConsentService(db_session).authorize_outbound_queue_message(queue)

    assert decision.allowed is False
    assert decision.reason == "contact consent is unknown"
    row = (
        await db_session.execute(
            select(ContactMessagingConsent).where(
                ContactMessagingConsent.contact_id == test_contact.id,
                ContactMessagingConsent.exact_chat_id == test_contact.whatsapp_id,
            )
        )
    ).scalar_one()
    assert row.status == "unknown"


@pytest.mark.asyncio
async def test_final_consent_fence_locks_contact_before_send(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-2026-10-24",
        owner_identity="OWNER",
    )
    queue_id = queue.id
    contact_id = test_contact.id
    await db_session.commit()

    # A separate transaction must not be able to begin inbound contact processing
    # while the final authorization fence is held through the transport attempt.
    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as worker_session, factory() as ingress_session:
        worker_queue = await worker_session.get(OutboundMessage, queue_id)
        decision = await ContactMessagingConsentService(
            worker_session
        ).authorize_outbound_queue_message(worker_queue)
        assert decision.allowed is True

        try:
            with pytest.raises(DBAPIError):
                await ingress_session.execute(
                    select(Contact.id)
                    .where(Contact.id == contact_id)
                    .with_for_update(nowait=True)
                )
        finally:
            await ingress_session.rollback()
            await worker_session.rollback()


@pytest.mark.asyncio
async def test_inbound_chat_remap_serializes_with_final_consent_mapping_lock(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-chat-remap-race",
        owner_identity="OWNER",
    )
    other = Contact(whatsapp_id="other-mapping-contact@c.us", chat_id="other-mapping-contact@c.us")
    db_session.add(other)
    await db_session.flush()
    other_id = int(other.id)
    other_whatsapp_id = other.whatsapp_id
    queue_id = int(queue.id)
    exact_chat_id = test_contact.whatsapp_id
    await db_session.commit()

    factory = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with factory() as dispatch_session, factory() as ingress_session:
        worker_queue = await dispatch_session.get(OutboundMessage, queue_id)
        decision = await ContactMessagingConsentService(
            dispatch_session
        ).authorize_outbound_queue_message(worker_queue)
        assert decision.allowed is True

        # This is the production Contact.chat_id writer. A second Contact attempting
        # to claim the already-authorized exact direct chat must wait on the same
        # transaction-scoped mapping lock before it can update its own row.
        normalized = SimpleNamespace(
            sender_id=other_whatsapp_id,
            sender_identity={},
            sender_name=None,
            chat_id=exact_chat_id,
            chat_type=SimpleNamespace(value="dm"),
        )
        remap_task = asyncio.create_task(InboundRouter(ingress_session)._get_or_create_contact(normalized))
        try:
            await asyncio.sleep(0.1)
            assert not remap_task.done(), "conflicting chat mapping must wait for the final consent transaction"
        finally:
            await dispatch_session.rollback()

        remapped_contact = await asyncio.wait_for(remap_task, timeout=2)
        assert int(remapped_contact.id) == other_id
        await ingress_session.commit()

    # Once the competing mapping commits, a later authorization sees ambiguity and
    # fails closed. The worker-level stale/remapped-destination regression separately
    # asserts zero mocked WAHA calls for this denial reason.
    async with factory() as verify_session:
        queued = await verify_session.get(OutboundMessage, queue_id)
        denied = await ContactMessagingConsentService(
            verify_session
        ).authorize_outbound_queue_message(queued)
        assert denied.allowed is False
        assert denied.reason == "current contact/chat mapping does not match recipient"


@pytest.mark.asyncio
async def test_explicit_owner_grant_allows_only_exact_durable_contact_chat(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    service = ContactMessagingConsentService(db_session)

    await service.grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-2026-10-24",
        owner_identity="OWNER",
    )
    decision = await service.authorize_outbound_queue_message(queue)

    assert decision.allowed is True
    assert decision.contact_id == test_contact.id
    assert decision.consent_id is not None


@pytest.mark.asyncio
async def test_inbound_opt_out_overrides_prior_grant_and_is_audited(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    service = ContactMessagingConsentService(db_session)
    await service.grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-2026-10-24",
        owner_identity="OWNER",
    )
    await service.record_inbound_opt_out(
        contact_id=test_contact.id,
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="inbound-message-123",
    )

    decision = await service.authorize_outbound_queue_message(queue)
    events = (
        await db_session.execute(
            __import__("sqlalchemy").select(ContactMessagingConsentEvent)
            .where(ContactMessagingConsentEvent.contact_id == test_contact.id)
            .order_by(ContactMessagingConsentEvent.id)
        )
    ).scalars().all()

    assert decision.allowed is False
    assert decision.reason == "contact has opted out"
    assert [event.event_type for event in events] == ["granted", "opted_out"]
    assert events[-1].evidence_ref == "inbound-message-123"


@pytest.mark.asyncio
async def test_opt_out_on_mapped_alias_blocks_other_alias_grant_and_dispatch(db_session, test_contact):
    target_chat_id = test_contact.whatsapp_id
    opt_out_alias = "333@c.us"
    test_contact.chat_id = opt_out_alias
    await db_session.flush()

    queue = await _queue_with_source(db_session, test_contact, target_chat_id)
    service = ContactMessagingConsentService(db_session)
    await service.grant_for_chat(
        exact_chat_id=target_chat_id,
        evidence_ref="owner-attested-before-alias-stop",
        owner_identity="OWNER",
    )
    await service.record_inbound_opt_out(
        contact_id=int(test_contact.id),
        exact_chat_id=opt_out_alias,
        evidence_ref="inbound-stop-on-alias",
    )

    decision = await service.authorize_outbound_queue_message(queue)
    assert decision.allowed is False
    assert decision.reason == "contact has opted out"

    with pytest.raises(ValueError, match="explicit contact re-consent"):
        await service.grant_for_chat(
            exact_chat_id=target_chat_id,
            evidence_ref="owner-grant-after-alias-stop",
            owner_identity="OWNER",
        )


@pytest.mark.asyncio
async def test_pending_opt_out_intent_on_mapped_alias_vetoes_contact(db_session, test_contact):
    opt_out_alias = "333@c.us"
    test_contact.chat_id = opt_out_alias
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO inbound_webhook_receipts (
                event_key, session_name, chat_id, message_id, opt_out_intent,
                status, claim_token, updated_at
            )
            VALUES (
                'alias-stop-pending-test', 'test', :chat_id, 'alias-stop-pending-test',
                TRUE, 'processing', 'test-claim-token', NOW()
            )
            """
        ),
        {"chat_id": opt_out_alias},
    )

    assert await ContactMessagingConsentService(
        db_session
    ).has_pending_opt_out_intent_for_contact(int(test_contact.id)) is True


@pytest.mark.asyncio
async def test_owner_grant_cannot_override_opt_out(db_session, test_contact):
    service = ContactMessagingConsentService(db_session)
    await service.record_inbound_opt_out(
        contact_id=test_contact.id,
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="inbound-message-123",
    )

    # An OWNER revoke must not rewrite a contact's terminal opt-out into a
    # state from which a later grant can bypass explicit contact re-consent.
    with pytest.raises(ValueError, match="terminal opt-out"):
        await service.revoke_for_chat(
            exact_chat_id=test_contact.whatsapp_id,
            evidence_ref="owner-revocation-after-optout",
            owner_identity="OWNER",
        )

    with pytest.raises(ValueError, match="explicit contact re-consent"):
        await service.grant_for_chat(
            exact_chat_id=test_contact.whatsapp_id,
            evidence_ref="owner-attested-again",
            owner_identity="OWNER",
        )

    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    decision = await service.authorize_outbound_queue_message(queue)
    assert decision.allowed is False
    assert decision.reason == "contact has opted out"


@pytest.mark.asyncio
async def test_terminal_opt_out_survives_contact_delete_and_recreation(db_session, test_contact):
    exact_chat_id = test_contact.whatsapp_id
    service = ContactMessagingConsentService(db_session)
    await service.record_inbound_opt_out(
        contact_id=int(test_contact.id),
        exact_chat_id=exact_chat_id,
        evidence_ref="inbound-stop-before-contact-delete",
    )
    await db_session.commit()

    # Live consent state is intentionally FK-cascaded, while the append-only event
    # history is not. Recreating the same Contact must not turn that history into
    # fresh UNKNOWN state which an OWNER grant can silently override.
    await db_session.delete(test_contact)
    await db_session.commit()

    replacement = Contact(
        whatsapp_id=exact_chat_id,
        chat_id=exact_chat_id,
        display_name="Recreated contact",
    )
    db_session.add(replacement)
    await db_session.flush()

    with pytest.raises(ValueError, match="explicit contact re-consent"):
        await ContactMessagingConsentService(db_session).grant_for_chat(
            exact_chat_id=exact_chat_id,
            evidence_ref="owner-grant-after-contact-recreation",
            owner_identity="OWNER",
        )

    live_state = await db_session.execute(
        select(ContactMessagingConsent.id).where(
            ContactMessagingConsent.contact_id == replacement.id,
            ContactMessagingConsent.exact_chat_id == exact_chat_id,
        )
    )
    assert live_state.scalar_one_or_none() is None

    history = (
        await db_session.execute(
            select(ContactMessagingConsentEvent).where(
                ContactMessagingConsentEvent.exact_chat_id == exact_chat_id,
                ContactMessagingConsentEvent.event_type == "opted_out",
            )
        )
    ).scalars().all()
    assert len(history) == 1
    assert history[0].evidence_ref == "inbound-stop-before-contact-delete"


@pytest.mark.asyncio
async def test_expired_consent_and_wrong_exact_chat_fail_closed(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    service = ContactMessagingConsentService(db_session)
    await service.grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-2026-10-24",
        owner_identity="OWNER",
    )
    row = (
        await db_session.execute(
            __import__("sqlalchemy").select(ContactMessagingConsent).where(
                ContactMessagingConsent.contact_id == test_contact.id,
                ContactMessagingConsent.exact_chat_id == test_contact.whatsapp_id,
            )
        )
    ).scalar_one()
    row.expires_at = utcnow() - timedelta(seconds=1)
    await db_session.flush()

    expired = await service.authorize_outbound_queue_message(queue)
    wrong_chat = OutboundMessage(
        chat_id="15550000002@c.us",
        message_text="reply",
        formatting_json={
            "inbound_message_id": queue.formatting_json["inbound_message_id"],
            "contact_id": test_contact.id,
            "delivery_policy": "approval_required",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
    )
    db_session.add(wrong_chat)
    await db_session.flush()
    mismatched = await service.authorize_outbound_queue_message(wrong_chat)

    assert expired.allowed is False
    assert expired.reason == "contact consent has expired"
    assert mismatched.allowed is False
    assert mismatched.reason == "exact durable contact/chat mapping is missing"


@pytest.mark.parametrize(
    "message,expected",
    [
        ("STOP", True),
        ("Please stop messaging me.", True),
        ("unsubscribe", True),
        ("STOP, PLEASE!", True),
        ("STOP 🙏", True),
        ("STOP🙏", True),
        ("Unsubscribe me 📵", True),
        ("ＳＴＯＰ", True),
        ("don't stop 😅", False),
        ("the bus stop 🚌", False),
        ("stop sending messages", True),
        ("PLEASE STOP SENDING MESSAGES!", True),
        ("stop all messages", True),
        ("STOP MESSAGING 🙏", True),
        ("stop texting", True),
        ("stop contacting", True),
        ("stop sending", True),
        ("unsubscribe please 📵", True),
        ("please unsubscribe", True),
        ("remove me from your list", True),
        ("take me off your list", True),
        ("unsubscribe me", True),
        ("Please unsubscribe me.", True),
        ("unsubscribe me please", True),
        ("I don't want any more messages", True),
        ("do not contact me again", True),
        ("stop the deployment", False),
        ("stop sending the deployment", False),
        ("stop messaging about the deployment", False),
        ("unsubscribe please send the report", False),
        ("please stop sending by later", False),
        ("don't stop", False),
        ("please stop by later", False),
        ("what is the status?", False),
    ],
)
def test_opt_out_parser_is_conservative_and_deterministic(message, expected):
    assert ContactMessagingConsentService.is_explicit_opt_out_message(message) is expected


@pytest.mark.asyncio
async def test_dispatch_lock_serializes_later_opt_out(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    service = ContactMessagingConsentService(db_session)
    await service.grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-race-1",
        owner_identity="OWNER",
    )
    await db_session.commit()

    queue_id = int(queue.id)
    contact_id = int(test_contact.id)
    chat_id = test_contact.whatsapp_id
    Session = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with Session() as dispatch_session, Session() as optout_session:
        dispatch_queue = await dispatch_session.get(OutboundMessage, queue_id)
        decision = await ContactMessagingConsentService(dispatch_session).authorize_outbound_queue_message(
            dispatch_queue
        )
        assert decision.allowed is True

        started = asyncio.Event()

        async def record_opt_out():
            started.set()
            await ContactMessagingConsentService(optout_session).record_inbound_opt_out(
                contact_id=contact_id,
                exact_chat_id=chat_id,
                evidence_ref="inbound-optout-race-1",
            )
            await optout_session.commit()

        task = asyncio.create_task(record_opt_out())
        await started.wait()
        await asyncio.sleep(0.05)
        assert not task.done(), "opt-out must wait while the dispatch transaction owns the consent row lock"

        await dispatch_session.commit()
        await asyncio.wait_for(task, timeout=3)

    db_session.expire_all()
    row = (
        await db_session.execute(
            select(ContactMessagingConsent).where(
                ContactMessagingConsent.contact_id == contact_id,
                ContactMessagingConsent.exact_chat_id == chat_id,
            )
        )
    ).scalar_one()
    assert row.status == "opted_out"


@pytest.mark.asyncio
async def test_opt_out_lock_wins_before_dispatch_authorization(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    await db_session.commit()

    queue_id = int(queue.id)
    contact_id = int(test_contact.id)
    chat_id = test_contact.whatsapp_id
    Session = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    async with Session() as optout_session, Session() as dispatch_session:
        # Match production lock order: exact-chat mapping, Contact row, then consent.
        await ContactMessagingConsentService.lock_exact_chat_mapping(optout_session, chat_id)
        await optout_session.execute(
            select(Contact.id)
            .where(Contact.id == contact_id)
            .with_for_update()
        )
        await ContactMessagingConsentService(optout_session).record_inbound_opt_out(
            contact_id=contact_id,
            exact_chat_id=chat_id,
            evidence_ref="inbound-optout-race-2",
        )

        started = asyncio.Event()

        async def authorize_dispatch():
            dispatch_queue = await dispatch_session.get(OutboundMessage, queue_id)
            started.set()
            return await ContactMessagingConsentService(dispatch_session).authorize_outbound_queue_message(
                dispatch_queue
            )

        task = asyncio.create_task(authorize_dispatch())
        await started.wait()
        await asyncio.sleep(0.05)
        assert not task.done(), "dispatch must wait for the in-flight opt-out transaction"

        await optout_session.commit()
        decision = await asyncio.wait_for(task, timeout=3)
        await dispatch_session.commit()

    assert decision.allowed is False
    assert decision.reason == "contact has opted out"


@pytest.mark.asyncio
async def test_first_insert_race_materializes_one_opted_out_row(db_session, test_contact):
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    await db_session.commit()

    queue_id = int(queue.id)
    contact_id = int(test_contact.id)
    chat_id = test_contact.whatsapp_id
    Session = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    start = asyncio.Event()

    async def dispatch_first_touch():
        async with Session() as session:
            dispatch_queue = await session.get(OutboundMessage, queue_id)
            await start.wait()
            decision = await ContactMessagingConsentService(session).authorize_outbound_queue_message(
                dispatch_queue
            )
            await session.commit()
            return decision

    async def opt_out_first_touch():
        async with Session() as session:
            await start.wait()
            # Match production lock order: exact-chat mapping, Contact row, then consent.
            await ContactMessagingConsentService.lock_exact_chat_mapping(session, chat_id)
            await session.execute(
                select(Contact.id)
                .where(Contact.id == contact_id)
                .with_for_update()
            )
            await ContactMessagingConsentService(session).record_inbound_opt_out(
                contact_id=contact_id,
                exact_chat_id=chat_id,
                evidence_ref="inbound-optout-first-insert",
            )
            await session.commit()

    dispatch_task = asyncio.create_task(dispatch_first_touch())
    optout_task = asyncio.create_task(opt_out_first_touch())
    start.set()
    decision, _ = await asyncio.gather(dispatch_task, optout_task)

    assert decision.allowed is False
    db_session.expire_all()
    rows = (
        await db_session.execute(
            select(ContactMessagingConsent).where(
                ContactMessagingConsent.contact_id == contact_id,
                ContactMessagingConsent.exact_chat_id == chat_id,
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].status == "opted_out"

@pytest.mark.asyncio
async def test_inbound_opt_out_rejects_contact_chat_mismatch_without_mutation(db_session, test_contact):
    service = ContactMessagingConsentService(db_session)

    with pytest.raises(ValueError, match="exact chat ID does not match durable contact"):
        await service.record_inbound_opt_out(
            contact_id=test_contact.id,
            exact_chat_id="15550000099@c.us",
            evidence_ref="inbound-message-mismatch",
        )

    rows = (
        await db_session.execute(
            select(ContactMessagingConsent).where(
                ContactMessagingConsent.contact_id == test_contact.id
            )
        )
    ).scalars().all()
    events = (
        await db_session.execute(
            select(ContactMessagingConsentEvent).where(
                ContactMessagingConsentEvent.contact_id == test_contact.id
            )
        )
    ).scalars().all()
    assert rows == []
    assert events == []

@pytest.mark.asyncio
async def test_consent_event_history_rejects_update_delete_and_truncate(db_session, test_contact):
    """The database trigger, not just service convention, preserves consent history."""
    service = ContactMessagingConsentService(db_session)
    await service.record_inbound_opt_out(
        contact_id=test_contact.id,
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="immutable-audit-event",
    )
    await db_session.commit()

    event = (
        await db_session.execute(
            select(ContactMessagingConsentEvent).where(
                ContactMessagingConsentEvent.contact_id == test_contact.id,
                ContactMessagingConsentEvent.exact_chat_id == test_contact.whatsapp_id,
                ContactMessagingConsentEvent.event_type == "opted_out",
            )
        )
    ).scalar_one()
    event_id = int(event.id)

    with pytest.raises(DBAPIError):
        await db_session.execute(
            text(
                "UPDATE contact_messaging_consent_events "
                "SET evidence_ref = :replacement WHERE id = :event_id"
            ),
            {"replacement": "tampered", "event_id": event_id},
        )
    await db_session.rollback()

    with pytest.raises(DBAPIError):
        await db_session.execute(
            text("DELETE FROM contact_messaging_consent_events WHERE id = :event_id"),
            {"event_id": event_id},
        )
    await db_session.rollback()

    with pytest.raises(DBAPIError):
        await db_session.execute(text("TRUNCATE TABLE contact_messaging_consent_events"))
    await db_session.rollback()

    persisted = (
        await db_session.execute(
            select(ContactMessagingConsentEvent).where(
                ContactMessagingConsentEvent.id == event_id
            )
        )
    ).scalar_one()
    assert persisted.evidence_ref == "immutable-audit-event"
    assert persisted.event_type == "opted_out"

@pytest.mark.asyncio
async def test_dispatch_denies_ambiguous_current_chat_mapping(db_session, test_contact):
    """A legacy duplicate chat_id must not inherit another contact's consent."""
    queue = await _queue_with_source(db_session, test_contact, test_contact.whatsapp_id)
    service = ContactMessagingConsentService(db_session)
    await service.grant_for_chat(
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="owner-attested-before-remap",
        owner_identity="OWNER",
    )

    # whatsapp_id is unique, but chat_id is nullable and not globally unique.
    # This simulates legacy or manually edited data where one exact destination
    # is claimed by two different Contact rows after the original grant.
    db_session.add(
        Contact(
            whatsapp_id="15550000002@c.us",
            chat_id=test_contact.whatsapp_id,
            display_name="Conflicting contact mapping",
        )
    )
    await db_session.flush()

    decision = await service.authorize_outbound_queue_message(queue)

    assert decision.allowed is False
    assert decision.reason == "current contact/chat mapping does not match recipient"

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.models.schema import (
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
async def test_owner_grant_cannot_override_opt_out(db_session, test_contact):
    service = ContactMessagingConsentService(db_session)
    await service.record_inbound_opt_out(
        contact_id=test_contact.id,
        exact_chat_id=test_contact.whatsapp_id,
        evidence_ref="inbound-message-123",
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
        ("I don't want any more messages", True),
        ("do not contact me again", True),
        ("stop the deployment", False),
        ("don't stop", False),
        ("what is the status?", False),
    ],
)
def test_opt_out_parser_is_conservative_and_deterministic(message, expected):
    assert ContactMessagingConsentService.is_explicit_opt_out_message(message) is expected

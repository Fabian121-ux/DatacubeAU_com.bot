from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.schema import Contact, Message, OutboundMessage
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.outbound_safety_limit_service import OutboundSafetyDecision, OutboundSafetyLimitService
from app.utils.time import utcnow
from app.workers import background_workers


class _BlockingWahaClient:
    """Mock transport that pauses after the worker's final authorization fence."""

    def __init__(self) -> None:
        self.entered_send = asyncio.Event()
        self.release_send = asyncio.Event()
        self.calls: list[tuple[str, str]] = []

    async def send_text(self, *, chat_id: str, text: str) -> dict[str, str]:
        self.calls.append((chat_id, text))
        self.entered_send.set()
        await asyncio.wait_for(self.release_send.wait(), timeout=5)
        return {"id": "mock-waha-message-id"}

    async def send_media(self, **_: object) -> dict[str, str]:
        raise AssertionError("this regression must use the single text-send path")


@pytest.mark.asyncio
async def test_owner_policy_disable_cannot_commit_during_final_worker_transport_attempt(
    db_session, test_contact, monkeypatch
):
    """The policy row lock must survive the final fence until the one send attempt ends."""
    now = utcnow()
    exact_chat_id = "222@c.us"
    body = "authorized once; policy disable must serialize"
    test_contact.whatsapp_id = exact_chat_id
    test_contact.chat_id = exact_chat_id

    inbound = Message(
        contact_id=test_contact.id,
        chat_id=exact_chat_id,
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(inbound)
    await db_session.flush()

    queue = OutboundMessage(
        chat_id=exact_chat_id,
        message_text=body,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": inbound.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(body),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.flush()

    policy_id = (
        await db_session.execute(
            text(
                """
                INSERT INTO contact_automation_policies (
                    contact_id, exact_chat_id, enabled, allowed_categories,
                    prohibited_categories, approval_required_categories, created_by
                )
                VALUES (
                    :contact_id, :chat_id, true, '["normal_reply"]'::jsonb,
                    '[]'::jsonb, '[]'::jsonb, 'test-owner'
                )
                RETURNING id
                """
            ),
            {"contact_id": test_contact.id, "chat_id": exact_chat_id},
        )
    ).scalar_one()

    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=exact_chat_id,
        evidence_ref="owner-attested-worker-race",
        owner_identity="OWNER",
    )
    await db_session.commit()

    sessions = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", sessions)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")

    safety_calls: list[int] = []

    async def allow_safety(self, message, *, now=None):
        safety_calls.append(int(message.id))
        return OutboundSafetyDecision(True, "within bounded outbound safety limits")

    monkeypatch.setattr(
        background_workers.OutboundSafetyLimitService,
        "authorize",
        allow_safety,
    )

    client = _BlockingWahaClient()
    worker_task = asyncio.create_task(background_workers._deliver_due_outbound_messages(client))
    owner_task = None
    update_started = asyncio.Event()
    disable_was_blocked_during_send = False

    try:
        await asyncio.wait_for(client.entered_send.wait(), timeout=5)

        async def disable_policy() -> None:
            async with sessions() as owner_session:
                update_started.set()
                await owner_session.execute(
                    text(
                        """
                        UPDATE contact_automation_policies
                        SET enabled = false, disabled_at = now(), updated_at = now()
                        WHERE id = :policy_id
                        """
                    ),
                    {"policy_id": policy_id},
                )
                await owner_session.commit()

        owner_task = asyncio.create_task(disable_policy())
        await asyncio.wait_for(update_started.wait(), timeout=5)
        await asyncio.sleep(0.05)
        disable_was_blocked_during_send = not owner_task.done()
    finally:
        # Never strand the mock worker if an assertion or timeout fails.
        client.release_send.set()

    processed = await asyncio.wait_for(worker_task, timeout=5)
    assert owner_task is not None
    await asyncio.wait_for(owner_task, timeout=5)

    assert disable_was_blocked_during_send, (
        "OWNER policy disable committed while the mock transport attempt was still blocked"
    )
    assert processed == 1
    # Initial claim plus a second check after the final policy/contact/consent fences.
    assert safety_calls == [int(queue.id), int(queue.id)]
    assert client.calls == [(exact_chat_id, body)]

    await db_session.refresh(queue)
    assert queue.status == "sent"

    policy_enabled = (
        await db_session.execute(
            text("SELECT enabled FROM contact_automation_policies WHERE id = :policy_id"),
            {"policy_id": policy_id},
        )
    ).scalar_one()
    assert policy_enabled is False


@pytest.mark.asyncio
async def test_final_safety_recheck_denies_before_any_transport_call(
    db_session, test_contact, monkeypatch
):
    now = utcnow()
    exact_chat_id = "222@c.us"
    body = "must not send after final safety recheck denies"
    test_contact.whatsapp_id = exact_chat_id
    test_contact.chat_id = exact_chat_id

    inbound = Message(
        contact_id=test_contact.id,
        chat_id=exact_chat_id,
        chat_type="dm",
        direction="inbound",
        message_text="original inbound",
        normalized_text="original inbound",
        message_type="text",
    )
    db_session.add(inbound)
    await db_session.flush()

    queue = OutboundMessage(
        chat_id=exact_chat_id,
        message_text=body,
        formatting_json={
            "delivery_policy": "approval_required",
            "inbound_message_id": inbound.id,
            "contact_id": test_contact.id,
            "content_sha256": OutboundAuthorizationService.content_hash(body),
            "response_category": "normal_reply",
        },
        status="pending",
        retry_count=0,
        max_retries=3,
        next_attempt_at=now - timedelta(seconds=1),
        updated_at=now - timedelta(seconds=1),
    )
    db_session.add(queue)
    await db_session.flush()

    await db_session.execute(
        text(
            """
            INSERT INTO contact_automation_policies (
                contact_id, exact_chat_id, enabled, allowed_categories,
                prohibited_categories, approval_required_categories, created_by
            )
            VALUES (
                :contact_id, :chat_id, true, '["normal_reply"]'::jsonb,
                '[]'::jsonb, '[]'::jsonb, 'test-owner'
            )
            """
        ),
        {"contact_id": test_contact.id, "chat_id": exact_chat_id},
    )
    await ContactMessagingConsentService(db_session).grant_for_chat(
        exact_chat_id=exact_chat_id,
        evidence_ref="owner-attested-final-safety-recheck",
        owner_identity="OWNER",
    )
    await db_session.commit()

    sessions = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", sessions)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")

    safety_calls = 0

    async def allow_initial_then_deny_final(self, message, *, now=None):
        nonlocal safety_calls
        safety_calls += 1
        if safety_calls == 1:
            return OutboundSafetyDecision(True, "initial reservation allowed")
        return OutboundSafetyDecision(False, "final reservation no longer allowed")

    monkeypatch.setattr(
        background_workers.OutboundSafetyLimitService,
        "authorize",
        allow_initial_then_deny_final,
    )

    class _NoSendClient:
        def __init__(self):
            self.calls: list[tuple[str, str]] = []

        async def send_text(self, *, chat_id: str, text: str) -> dict[str, str]:
            self.calls.append((chat_id, text))
            return {"id": "unexpected"}

    client = _NoSendClient()
    processed = await background_workers._deliver_due_outbound_messages(client)

    assert processed == 1
    assert safety_calls == 2
    assert client.calls == []
    await db_session.refresh(queue)
    assert queue.status == "deferred"


@pytest.mark.asyncio
async def test_stale_in_flight_reservation_blocks_second_worker_after_final_fence_wait(
    db_session, test_contact, monkeypatch
):
    """An old timestamp cannot free global rate capacity while worker one waits at its final fence."""
    t0 = utcnow()
    clock = [t0]
    first_chat_id = "222@c.us"
    second_chat_id = "333@c.us"
    test_contact.whatsapp_id = first_chat_id
    test_contact.chat_id = first_chat_id
    other_contact = Contact(
        whatsapp_id=second_chat_id,
        chat_id=second_chat_id,
        display_name="Second contact for global rate-limit regression",
    )
    db_session.add(other_contact)
    await db_session.flush()

    first_inbound = Message(
        contact_id=test_contact.id, chat_id=first_chat_id, chat_type="dm",
        direction="inbound", message_text="first inbound",
        normalized_text="first inbound", message_type="text",
    )
    second_inbound = Message(
        contact_id=other_contact.id, chat_id=second_chat_id, chat_type="dm",
        direction="inbound", message_text="second inbound",
        normalized_text="second inbound", message_type="text",
    )
    db_session.add_all([first_inbound, second_inbound])
    await db_session.flush()

    first_body = "first reserved message"
    second_body = "second message must be globally rate limited"
    first_common = {
        "delivery_policy": "approval_required",
        "inbound_message_id": first_inbound.id,
        "contact_id": test_contact.id,
        "response_category": "normal_reply",
    }
    second_common = {
        "delivery_policy": "approval_required",
        "inbound_message_id": second_inbound.id,
        "contact_id": other_contact.id,
        "response_category": "normal_reply",
    }
    first = OutboundMessage(
        chat_id=first_chat_id,
        message_text=first_body,
        formatting_json={**first_common, "content_sha256": OutboundAuthorizationService.content_hash(first_body)},
        status="pending", retry_count=0, max_retries=3,
        next_attempt_at=t0 - timedelta(seconds=1),
        updated_at=t0 - timedelta(seconds=1),
    )
    second = OutboundMessage(
        chat_id=second_chat_id,
        message_text=second_body,
        formatting_json={**second_common, "content_sha256": OutboundAuthorizationService.content_hash(second_body)},
        status="pending", retry_count=0, max_retries=3,
        next_attempt_at=t0 + timedelta(seconds=90),
        updated_at=t0,
    )
    db_session.add_all([first, second])
    await db_session.flush()

    for contact_id, chat_id in ((test_contact.id, first_chat_id), (other_contact.id, second_chat_id)):
        await db_session.execute(
            text(
                """
                INSERT INTO contact_automation_policies (
                    contact_id, exact_chat_id, enabled, allowed_categories,
                    prohibited_categories, approval_required_categories, created_by
                )
                VALUES (
                    :contact_id, :chat_id, true, '[\"normal_reply\"]'::jsonb,
                    '[]'::jsonb, '[]'::jsonb, 'test-owner'
                )
                """
            ),
            {"contact_id": contact_id, "chat_id": chat_id},
        )
        await ContactMessagingConsentService(db_session).grant_for_chat(
            exact_chat_id=chat_id,
            evidence_ref=f"owner-attested-stale-reservation-race-{contact_id}",
            owner_identity="OWNER",
        )
    await db_session.commit()

    sessions = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    monkeypatch.setattr(background_workers, "SessionLocal", sessions)
    monkeypatch.setattr(background_workers.settings, "owner_whatsapp_ids", "111@c.us")
    monkeypatch.setattr(background_workers, "utcnow", lambda: clock[0])
    monkeypatch.setattr(OutboundSafetyLimitService, "GLOBAL_PER_MINUTE", 1)

    final_fence_reached = asyncio.Event()
    release_final_fence = asyncio.Event()
    original_consent_authorize = ContactMessagingConsentService.authorize_outbound_queue_message
    first_id = int(first.id)

    async def pause_first_at_consent(self, message, *, now=None):
        if int(message.id) == first_id:
            final_fence_reached.set()
            await asyncio.wait_for(release_final_fence.wait(), timeout=5)
        return await original_consent_authorize(self, message, now=now)

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "authorize_outbound_queue_message",
        pause_first_at_consent,
    )

    first_client = _BlockingWahaClient()
    first_worker = asyncio.create_task(background_workers._deliver_due_outbound_messages(first_client))
    try:
        await asyncio.wait_for(final_fence_reached.wait(), timeout=5)
        # Model a wait longer than the old one-minute window without real-time sleeping.
        # The first queue row remains locked by worker one while worker two evaluates row two.
        clock[0] = t0 + timedelta(minutes=2)

        class _NoSendClient:
            def __init__(self):
                self.calls: list[tuple[str, str]] = []

            async def send_text(self, *, chat_id: str, text: str) -> dict[str, str]:
                self.calls.append((chat_id, text))
                return {"id": "unexpected-second-worker-send"}

            async def send_media(self, **_: object) -> dict[str, str]:
                raise AssertionError("this regression must use the single text-send path")

        second_client = _NoSendClient()
        second_processed = await asyncio.wait_for(
            background_workers._deliver_due_outbound_messages(second_client), timeout=5
        )
        assert second_processed == 0
        assert second_client.calls == []
        await db_session.refresh(second)
        assert second.status == "deferred"
        assert "global outbound safety rate limit reached" in (second.error_message or "")

        release_final_fence.set()
        await asyncio.wait_for(first_client.entered_send.wait(), timeout=5)
        first_client.release_send.set()
        first_processed = await asyncio.wait_for(first_worker, timeout=5)
    finally:
        release_final_fence.set()
        first_client.release_send.set()
        if not first_worker.done():
            await asyncio.wait_for(first_worker, timeout=5)

    assert first_processed == 1
    assert first_client.calls == [(first_chat_id, first_body)]
    await db_session.refresh(first)
    assert first.status == "sent"
    await db_session.refresh(second)
    assert second.status == "deferred"

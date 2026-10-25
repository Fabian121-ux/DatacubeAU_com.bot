from __future__ import annotations

import asyncio
from datetime import timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.models.schema import Message, OutboundMessage
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.outbound_safety_limit_service import OutboundSafetyDecision
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
    assert safety_calls == [queue_id, queue_id]
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

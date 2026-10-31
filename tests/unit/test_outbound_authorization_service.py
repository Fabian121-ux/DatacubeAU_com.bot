import asyncio
from types import SimpleNamespace

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.services.outbound_authorization_service import (
    AuthorizationContext,
    AuthorizationDecision,
    OutboundAuthorizationService,
)


def _message(*, message_id=10, chat_id="222@c.us", text="hello", metadata=None):
    return SimpleNamespace(
        id=message_id,
        chat_id=chat_id,
        message_text=text,
        formatting_json=metadata,
    )


def test_context_requires_exact_durable_source_contact_and_hash():
    digest = OutboundAuthorizationService.content_hash("hello")
    message = _message(
        metadata={
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
        }
    )

    context = OutboundAuthorizationService.context_from_queue_message(message)

    assert context is not None
    assert context.outbound_queue_id == 10
    assert context.inbound_message_id == 5
    assert context.contact_id == 7
    assert context.target_chat_id == "222@c.us"
    assert context.response_category == "normal_reply"
    assert context.content_sha256 == digest


def test_context_fails_closed_when_authority_metadata_is_missing():
    assert OutboundAuthorizationService.context_from_queue_message(_message(metadata={})) is None
    assert OutboundAuthorizationService.context_from_queue_message(_message(metadata=None)) is None


def test_context_fails_closed_when_content_changes_after_authority_stamp():
    digest = OutboundAuthorizationService.content_hash("approved text")
    message = _message(
        text="different text",
        metadata={
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
        },
    )

    assert OutboundAuthorizationService.context_from_queue_message(message) is None


def test_content_hash_is_deterministic_and_content_bound():
    assert OutboundAuthorizationService.content_hash("same") == OutboundAuthorizationService.content_hash("same")
    assert OutboundAuthorizationService.content_hash("same") != OutboundAuthorizationService.content_hash("different")


def test_authority_context_preserves_whatsapp_safe_formatting_exactly():
    text = "> quoted line\n\n*Important* uses `inline code`.\n\nFinal paragraph."
    digest = OutboundAuthorizationService.content_hash(text)
    message = _message(
        text=text,
        metadata={
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
        },
    )

    context = OutboundAuthorizationService.context_from_queue_message(message)

    assert context is not None
    assert message.message_text == text
    assert context.content_sha256 == digest
    assert OutboundAuthorizationService.content_hash(text.replace("\n\n", "\n")) != digest


@pytest.mark.asyncio
async def test_authorize_queue_message_fails_closed_before_database_lookup_when_context_missing(monkeypatch):
    service = OutboundAuthorizationService(SimpleNamespace())
    called = False

    async def _authorize(*args, **kwargs):
        nonlocal called
        called = True
        return AuthorizationDecision(True, "owner_approval", "should not run", approval_id=1)

    monkeypatch.setattr(service, "authorize", _authorize)

    context, decision = await service.authorize_queue_message(_message(metadata={}))

    assert context is None
    assert decision.allowed is False
    assert decision.authority_type == "none"
    assert "missing exact durable authority context" in decision.reason
    assert called is False


@pytest.mark.asyncio
async def test_authorize_queue_message_delegates_only_after_exact_context_validation(monkeypatch):
    digest = OutboundAuthorizationService.content_hash("hello")
    message = _message(
        metadata={
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
        }
    )
    service = OutboundAuthorizationService(SimpleNamespace())
    observed = None

    async def _authorize(context, *, now=None):
        nonlocal observed
        observed = context
        return AuthorizationDecision(True, "owner_approval", "exact active owner approval", approval_id=9)

    monkeypatch.setattr(service, "authorize", _authorize)

    context, decision = await service.authorize_queue_message(message)

    assert context is observed
    assert context is not None
    assert context.outbound_queue_id == 10
    assert decision.allowed is True
    assert decision.approval_id == 9


@pytest.mark.asyncio
async def test_contact_policy_authorization_locks_policy_until_dispatch_transaction_finishes():
    """A concurrent OWNER disable must serialize behind a policy-based send fence."""
    class Result:
        def __init__(self, *, scalar=None, mapping=None):
            self.scalar = scalar
            self.mapping = mapping

        def scalar_one_or_none(self):
            return self.scalar

        def mappings(self):
            return self

        def first(self):
            return self.mapping

    class Session:
        def __init__(self):
            self.statements = []

        async def execute(self, statement, params=None):
            sql = str(statement)
            self.statements.append(sql)
            if "FROM outbound_approvals" in sql:
                return Result(scalar=None)
            if "FROM contact_automation_policies" in sql:
                return Result(mapping={
                    "id": 41,
                    "allowed_categories": ["normal_reply"],
                    "prohibited_categories": [],
                    "approval_required_categories": [],
                    "quiet_hours_json": None,
                })
            raise AssertionError(f"Unexpected authorization query: {sql}")

    session = Session()
    context = AuthorizationContext(
        outbound_queue_id=91,
        inbound_message_id=51,
        contact_id=17,
        target_chat_id="2348012345678@c.us",
        content_sha256="a" * 64,
        response_category="normal_reply",
    )

    decision = await OutboundAuthorizationService(session).authorize(context)

    assert decision.allowed is True
    assert decision.authority_type == "contact_policy"
    policy_sql = next(sql for sql in session.statements if "FROM contact_automation_policies" in sql)
    assert "FOR UPDATE" in policy_sql.upper()


@pytest.mark.asyncio
async def test_contact_policy_disable_and_authorization_serialize_in_both_orders(db_session, test_contact):
    """Real PostgreSQL sessions prove policy disable cannot race a final authorization."""
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
            {"contact_id": test_contact.id, "chat_id": test_contact.whatsapp_id},
        )
    ).scalar_one()
    await db_session.commit()

    sessions = async_sessionmaker(bind=db_session.bind, expire_on_commit=False)
    context = AuthorizationContext(
        outbound_queue_id=91001,
        inbound_message_id=91002,
        contact_id=test_contact.id,
        target_chat_id=test_contact.whatsapp_id,
        content_sha256="a" * 64,
        response_category="normal_reply",
    )

    # Dispatch authorization wins the row lock first: an OWNER disable must wait
    # until the dispatch transaction releases the policy lock.
    async with sessions() as dispatch_session, sessions() as owner_session:
        decision = await OutboundAuthorizationService(dispatch_session).authorize(context)
        assert decision.allowed is True
        assert decision.authority_type == "contact_policy"

        update_started = asyncio.Event()

        async def disable_policy():
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

        update_task = asyncio.create_task(disable_policy())
        await update_started.wait()
        await asyncio.sleep(0.05)
        assert not update_task.done(), "policy disable must wait for the authorization transaction"
        await dispatch_session.commit()
        await asyncio.wait_for(update_task, timeout=3)

    # Conversely, if the OWNER disable already owns the row lock, authorization
    # must wait and then observe the disabled policy rather than approve from stale state.
    async with sessions() as owner_session, sessions() as dispatch_session:
        await owner_session.execute(
            text(
                """
                UPDATE contact_automation_policies
                SET enabled = true, disabled_at = NULL, updated_at = now()
                WHERE id = :policy_id
                """
            ),
            {"policy_id": policy_id},
        )
        await owner_session.commit()
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

        authorization_started = asyncio.Event()

        async def authorize_while_disable_is_uncommitted():
            authorization_started.set()
            return await OutboundAuthorizationService(dispatch_session).authorize(context)

        authorization_task = asyncio.create_task(authorize_while_disable_is_uncommitted())
        await authorization_started.wait()
        await asyncio.sleep(0.05)
        assert not authorization_task.done(), "authorization must wait for the in-flight OWNER disable"
        await owner_session.commit()
        decision = await asyncio.wait_for(authorization_task, timeout=3)
        await dispatch_session.commit()

    assert decision.allowed is False
    assert decision.authority_type == "none"
    assert decision.reason == "no exact active owner approval or contact automation policy"

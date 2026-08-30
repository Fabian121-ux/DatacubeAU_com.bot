from types import SimpleNamespace

import pytest

from app.services.outbound_authorization_service import (
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
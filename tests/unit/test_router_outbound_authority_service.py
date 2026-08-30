from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.router_outbound_authority_service import RouterOutboundAuthorityService


@pytest.mark.asyncio
async def test_prepare_external_reply_stamps_exact_authority_and_defers(monkeypatch):
    session = AsyncMock()
    service = RouterOutboundAuthorityService(session)
    create_pending = AsyncMock(return_value=41)
    monkeypatch.setattr(service.authorization, "create_pending_approval", create_pending)
    queue_message = SimpleNamespace(
        id=17,
        chat_id="2348012345678@c.us",
        message_text="Hello there",
        formatting_json={"whatsapp_message_format": "standard"},
        status="pending",
    )

    prepared = await service.prepare_external_reply(
        queue_message,
        inbound_message_id=9,
        contact_id=3,
        response_category="Normal_Reply",
    )

    expected_hash = OutboundAuthorizationService.content_hash("Hello there")
    assert queue_message.status == "deferred"
    assert queue_message.formatting_json["delivery_policy"] == "approval_required"
    assert queue_message.formatting_json["reply_deferred"] is True
    assert queue_message.formatting_json["inbound_message_id"] == 9
    assert queue_message.formatting_json["contact_id"] == 3
    assert queue_message.formatting_json["response_category"] == "normal_reply"
    assert queue_message.formatting_json["content_sha256"] == expected_hash
    assert prepared.approval_id == 41
    assert prepared.context.outbound_queue_id == 17
    assert prepared.context.target_chat_id == "2348012345678@c.us"
    create_pending.assert_awaited_once_with(context=prepared.context)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "queue_id,inbound_id,contact_id,chat_id",
    [
        (0, 9, 3, "2348012345678@c.us"),
        (17, 0, 3, "2348012345678@c.us"),
        (17, 9, 0, "2348012345678@c.us"),
        (17, 9, 3, ""),
    ],
)
async def test_prepare_external_reply_fails_closed_without_exact_durable_context(
    monkeypatch,
    queue_id,
    inbound_id,
    contact_id,
    chat_id,
):
    session = AsyncMock()
    service = RouterOutboundAuthorityService(session)
    create_pending = AsyncMock(return_value=41)
    monkeypatch.setattr(service.authorization, "create_pending_approval", create_pending)
    queue_message = SimpleNamespace(
        id=queue_id,
        chat_id=chat_id,
        message_text="Hello there",
        formatting_json={},
        status="pending",
    )

    with pytest.raises(ValueError):
        await service.prepare_external_reply(
            queue_message,
            inbound_message_id=inbound_id,
            contact_id=contact_id,
        )

    create_pending.assert_not_awaited()

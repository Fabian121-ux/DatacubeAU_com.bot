from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.router_outbound_authority_service import RouterOutboundAuthorityService


@pytest.mark.asyncio
async def test_prepare_external_reply_stamps_exact_authority_and_defers(monkeypatch):
    session = AsyncMock()
    service = RouterOutboundAuthorityService(session)
    create_pending = AsyncMock(return_value=41)
    coalesce = AsyncMock(return_value=[9])
    monkeypatch.setattr(service.authorization, "create_pending_approval", create_pending)
    monkeypatch.setattr(service, "_coalesce_recent_pending", coalesce)
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
    assert queue_message.formatting_json["source_inbound_message_ids"] == [9]
    assert queue_message.formatting_json["contact_id"] == 3
    assert queue_message.formatting_json["response_category"] == "normal_reply"
    assert queue_message.formatting_json["content_sha256"] == expected_hash
    assert prepared.approval_id == 41
    assert prepared.context.outbound_queue_id == 17
    assert prepared.context.target_chat_id == "2348012345678@c.us"
    create_pending.assert_awaited_once_with(context=prepared.context)


@pytest.mark.asyncio
async def test_prepare_external_reply_uses_only_service_coalesced_source_ids(monkeypatch):
    session = AsyncMock()
    service = RouterOutboundAuthorityService(session)
    create_pending = AsyncMock(return_value=42)
    coalesce = AsyncMock(return_value=[8, 9, 10])
    monkeypatch.setattr(service.authorization, "create_pending_approval", create_pending)
    monkeypatch.setattr(service, "_coalesce_recent_pending", coalesce)
    queue_message = SimpleNamespace(
        id=18,
        chat_id="2348012345678@c.us",
        message_text="Second message",
        formatting_json={"source_inbound_message_ids": [999, 1000]},
        status="pending",
    )

    await service.prepare_external_reply(
        queue_message,
        inbound_message_id=10,
        contact_id=3,
    )

    assert queue_message.formatting_json["source_inbound_message_ids"] == [8, 9, 10]


@pytest.mark.asyncio
async def test_coalesce_same_contact_supersedes_one_pending_candidate_and_preserves_sources():
    session = AsyncMock()
    lock_result = MagicMock()
    candidate_result = MagicMock()
    candidate_result.mappings.return_value.first.return_value = {
        "queue_id": 17,
        "approval_id": 41,
        "formatting_json": {
            "contact_id": 3,
            "inbound_message_id": 8,
            "source_inbound_message_ids": [8, 9],
            "response_category": "normal_reply",
        },
    }
    session.execute.side_effect = [lock_result, candidate_result, MagicMock(), MagicMock()]
    service = RouterOutboundAuthorityService(session)
    current = SimpleNamespace(id=18, media_url=None, media_type=None)

    sources = await service._coalesce_recent_pending(
        current,
        inbound_message_id=10,
        contact_id=3,
        target_chat_id="2348012345678@c.us",
        response_category="normal_reply",
    )

    assert sources == [8, 9, 10]
    assert session.execute.await_count == 4
    candidate_params = session.execute.await_args_list[1].args[1]
    assert candidate_params["target_chat_id"] == "2348012345678@c.us"
    assert candidate_params["contact_id"] == "3"
    assert candidate_params["response_category"] == "normal_reply"
    reject_params = session.execute.await_args_list[2].args[1]
    supersede_params = session.execute.await_args_list[3].args[1]
    assert reject_params == {"approval_id": 41}
    assert supersede_params == {"queue_id": 17}


@pytest.mark.asyncio
async def test_coalesce_contact_isolation_query_is_exact_contact_and_chat_bound():
    session = AsyncMock()
    candidate_result = MagicMock()
    candidate_result.mappings.return_value.first.return_value = None
    session.execute.side_effect = [MagicMock(), candidate_result]
    service = RouterOutboundAuthorityService(session)
    current = SimpleNamespace(id=22, media_url=None, media_type=None)

    sources = await service._coalesce_recent_pending(
        current,
        inbound_message_id=12,
        contact_id=7,
        target_chat_id="2348099999999@c.us",
        response_category="normal_reply",
    )

    assert sources == [12]
    params = session.execute.await_args_list[1].args[1]
    assert params["contact_id"] == "7"
    assert params["target_chat_id"] == "2348099999999@c.us"


@pytest.mark.asyncio
async def test_coalesce_does_not_supersede_media_candidate():
    session = AsyncMock()
    service = RouterOutboundAuthorityService(session)
    current = SimpleNamespace(id=22, media_url="https://example.invalid/file", media_type="image")

    sources = await service._coalesce_recent_pending(
        current,
        inbound_message_id=12,
        contact_id=7,
        target_chat_id="2348099999999@c.us",
        response_category="normal_reply",
    )

    assert sources == [12]
    session.execute.assert_not_awaited()


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
    coalesce = AsyncMock(return_value=[inbound_id] if inbound_id else [])
    monkeypatch.setattr(service.authorization, "create_pending_approval", create_pending)
    monkeypatch.setattr(service, "_coalesce_recent_pending", coalesce)
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

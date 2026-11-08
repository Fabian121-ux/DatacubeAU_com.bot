from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

import app.core.router as router_module
from app.api.deps import require_admin_session
from app.core.reply_planner import PlannedReply
from app.db import get_db_session
from app.main import app
from app.models.enums import DecisionType
from app.models.schema import AuditLog


class _NoTakeover:
    def __init__(self, _session):
        pass

    async def should_wait_for_fabian_first(self, *, chat_id: str) -> bool:
        return False


class _NoOwnerCommand:
    def __init__(self, _session):
        pass

    async def handle(self, _normalized, _contact):
        return None


class _ApprovalRequiredAuthority:
    def __init__(self, _session):
        pass

    async def prepare_external_reply(
        self,
        queue_message,
        *,
        inbound_message_id: int,
        contact_id: int,
        response_category: str,
    ):
        assert queue_message.status == "deferred"
        assert inbound_message_id > 0
        assert contact_id > 0
        return SimpleNamespace(
            approval_id=731,
            context=SimpleNamespace(response_category=response_category),
        )


@pytest.mark.asyncio
async def test_external_route_persists_late_approval_and_recent_api_exposes_internet_used(
    db_session,
    test_contact,
    normalized_dm_message,
    monkeypatch,
):
    """Exercise the real router commit and admin projection without any WAHA call."""
    router = router_module.InboundRouter(db_session)
    monkeypatch.setattr(router.normalizer, "normalize", lambda _event: normalized_dm_message)
    monkeypatch.setattr(router, "_is_owner_chat_id", lambda _chat_id: False)
    monkeypatch.setattr(router_module, "ConversationTakeoverService", _NoTakeover)
    monkeypatch.setattr(router_module, "OwnerCommandService", _NoOwnerCommand)
    monkeypatch.setattr(router_module, "RouterOutboundAuthorityService", _ApprovalRequiredAuthority)
    monkeypatch.setattr(
        router_module,
        "effective_summary_thresholds",
        AsyncMock(return_value=[25, 50, 100]),
    )

    planned = PlannedReply(
        decision_type=DecisionType.STATIC_REPLY,
        reason="test internet-backed result",
        should_reply=True,
        reply_text="A grounded answer.",
        source_diagnostics={
            "source": "Internet",
            "internet": {"success": True},
            "router_analytics": {
                "hits": {"internet": 1},
                "selected_source": "Internet",
            },
        },
    )

    async def _plan(*_args, **_kwargs):
        return planned

    monkeypatch.setattr(router, "_plan_with_owner_typing", _plan)

    memory = router.reply_planner.memory_service
    monkeypatch.setattr(memory, "ensure_relationship_profile", AsyncMock())
    monkeypatch.setattr(memory, "extract_profile_from_message", AsyncMock(return_value=[]))
    monkeypatch.setattr(memory, "log_conversation_event", AsyncMock(return_value=None))
    monkeypatch.setattr(memory, "parse_summary_thresholds", lambda _value: [25, 50, 100])
    monkeypatch.setattr(memory, "generate_due_summaries", AsyncMock(return_value=[]))
    monkeypatch.setattr(router.reply_planner.bot_config, "get", AsyncMock(return_value="25,50,100"))
    monkeypatch.setattr(router.reply_planner, "cache_answer_if_reusable", AsyncMock())

    result = await router.process_event({"test": "external-message"})

    assert result["action"] == "deferred"
    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "router_decision")
            .order_by(AuditLog.id.desc())
            .limit(1)
        )
    ).scalars().first()
    assert audit is not None
    assert audit.details_json["source_diagnostics"]["outbound_authority"] == {
        "approval_required": True,
        "approval_id": 731,
        "response_category": "normal_reply",
    }
    assert audit.details_json["internet_used"] is True

    previous_overrides = app.dependency_overrides.copy()

    async def _override_db_session():
        yield db_session

    app.dependency_overrides[get_db_session] = _override_db_session
    app.dependency_overrides[require_admin_session] = lambda: object()
    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as client:
            response = await client.get(
                "/admin/router-decisions/recent",
                params={"limit": 50},
            )
        assert response.status_code == 200
        payload = response.json()
        item = next(
            row for row in payload["items"]
            if row["message_id"] == result["inbound_message_id"]
        )
        assert item["internet_used"] is True
        assert item["source_diagnostics"]["outbound_authority"]["approval_id"] == 731
        assert item["source_diagnostics"]["outbound_authority"]["response_category"] == "normal_reply"
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous_overrides)

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, Contact
from app.services.memory_service import MemoryService
from app.services.tool_dispatcher_service import ToolDispatcherService, ToolExecutionContext


LAGOS = ZoneInfo("Africa/Lagos")


@pytest.mark.asyncio
async def test_owner_send_message_dispatches_to_existing_scheduler(db_session):
    contact = Contact(
        whatsapp_id="2348011111111@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "whatsapp.send_message",
        {
            "target": "Amanda Christabel",
            "text": "the document is ready",
            "scheduled_for": datetime(2026, 8, 25, 9, 0, tzinfo=LAGOS),
            "timezone": "Africa/Lagos",
        },
        context=ToolExecutionContext(permission="owner", idempotency_key="tool-dispatch-amanda"),
    )

    assert result["tool"] == "whatsapp.send_message"
    assert result["handler_target"] == "scheduled_action.whatsapp_send_message"
    assert result["result"]["target_contact_id"] == contact.id
    action = (await db_session.execute(select(ScheduledAction))).scalar_one()
    assert action.idempotency_key == "tool-dispatch-amanda"
    assert action.payload_json == {"text": "the document is ready"}


@pytest.mark.asyncio
async def test_find_contact_is_executable_read_tool_with_resolution_provenance(db_session):
    contact = Contact(
        whatsapp_id="2348022222222@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        push_name="Mandy",
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "whatsapp.find_contact",
        {"query": "Amanda Christabel", "limit": 3},
        context=ToolExecutionContext(permission="owner"),
    )

    assert result["tool"] == "whatsapp.find_contact"
    assert result["handler_target"] == "contact_intelligence.resolve"
    assert result["result"]["status"] == "resolved"
    assert result["result"]["match"]["contact_id"] == contact.id
    assert result["result"]["match"]["matched_field"] in {"contact_name", "display_name"}

    audit = (
        await db_session.execute(
            select(AuditLog)
            .where(AuditLog.action == "tool_execution_accepted")
            .where(AuditLog.entity_id == str(contact.id))
        )
    ).scalar_one()
    assert audit.details_json["tool"] == "whatsapp.find_contact"
    assert "Amanda" not in str(audit.details_json)


@pytest.mark.asyncio
async def test_find_contact_limit_one_preserves_ambiguity(db_session):
    db_session.add_all(
        [
            Contact(
                whatsapp_id="2348022222201@c.us",
                display_name="Amanda James",
                contact_name="Amanda James",
            ),
            Contact(
                whatsapp_id="2348022222202@c.us",
                display_name="Amanda Jones",
                contact_name="Amanda Jones",
            ),
        ]
    )
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "whatsapp.find_contact",
        {"query": "Amanda", "limit": 1},
        context=ToolExecutionContext(permission="owner"),
    )

    assert result["result"]["status"] == "ambiguous"
    assert result["result"]["match"] is None
    assert len(result["result"]["candidates"]) == 1


@pytest.mark.asyncio
async def test_memory_search_uses_existing_contact_and_matching_memory_evidence(db_session):
    contact = Contact(
        whatsapp_id="2348033333333@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
    )
    db_session.add(contact)
    await db_session.flush()

    memory = MemoryService(db_session)
    await memory.upsert_memory(
        contact.id,
        display_name="Amanda Christabel",
        interests="AI systems",
        projects="Datacube launch",
        relationship_type="friend",
    )
    await memory.log_timeline_event(
        contact.id,
        topic="Datacube launch",
        summary="Discussed the Datacube launch and AI integration plan.",
        importance_score=0.9,
    )

    result = await ToolDispatcherService(db_session).execute(
        "memory.search",
        {"query": "Datacube", "contact": "Amanda Christabel", "limit": 5},
        context=ToolExecutionContext(permission="owner"),
    )

    payload = result["result"]
    assert result["handler_target"] == "memory.search"
    assert payload["contact_id"] == contact.id
    assert payload["contact_resolution"]["status"] == "resolved"
    assert payload["query_matched"] is True
    assert payload["profile"]["display_name"] == "Amanda Christabel"
    assert payload["profile"]["projects"] == "Datacube launch"
    assert "interests" not in payload["profile"]
    assert any(item["topic"] == "Datacube launch" for item in payload["timeline_entries"])
    assert "Datacube launch" in payload["context_text"]
    assert payload["retrieved_item_count"] >= 2


@pytest.mark.asyncio
async def test_memory_search_includes_enabled_managed_memory_facts(db_session):
    contact = Contact(
        whatsapp_id="2348033333399@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
    )
    db_session.add(contact)
    await db_session.flush()

    memory = MemoryService(db_session)
    await memory.upsert_memory(contact.id, display_name="Amanda Christabel")
    enabled = await memory.log_memory_fact(
        contact.id,
        memory_text="proposal status: Amanda already received the proposal",
        source="owner_memory",
        confidence=0.95,
    )
    disabled = await memory.log_memory_fact(
        contact.id,
        memory_text="proposal status: obsolete draft was not received",
        source="owner_memory",
        confidence=0.4,
    )
    disabled.is_enabled = False
    await db_session.flush()

    result = await ToolDispatcherService(db_session).execute(
        "memory.search",
        {"query": "proposal", "contact": "Amanda Christabel", "limit": 5},
        context=ToolExecutionContext(permission="owner"),
    )

    payload = result["result"]
    assert payload["query_matched"] is True
    assert [item["id"] for item in payload["memory_facts"]] == [enabled.id]
    assert "already received the proposal" in payload["context_text"]
    assert "obsolete draft" not in payload["context_text"]
    assert "Managed Memory Fact" in payload["used_sections"]


@pytest.mark.asyncio
async def test_memory_search_returns_no_unrelated_fallback_context(db_session):
    contact = Contact(
        whatsapp_id="2348033333388@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
    )
    db_session.add(contact)
    await db_session.flush()

    memory = MemoryService(db_session)
    await memory.upsert_memory(contact.id, display_name="Amanda Christabel", projects="Datacube launch")
    await memory.log_timeline_event(
        contact.id,
        topic="Datacube launch",
        summary="Discussed the Datacube launch.",
        importance_score=0.9,
    )
    await memory.create_summary(
        contact.id,
        summary="Amanda and Fabian discussed Datacube delivery.",
        topics=["Datacube"],
        message_count=20,
    )

    result = await ToolDispatcherService(db_session).execute(
        "memory.search",
        {"query": "nonexistent scholarship", "contact": "Amanda Christabel", "limit": 5},
        context=ToolExecutionContext(permission="owner"),
    )

    payload = result["result"]
    assert payload["query_matched"] is False
    assert payload["profile"] == {}
    assert payload["memory_facts"] == []
    assert payload["timeline_entries"] == []
    assert payload["summaries"] == []
    assert payload["context_text"] == ""
    assert payload["retrieved_item_count"] == 0
    assert payload["used_sections"] == []


@pytest.mark.asyncio
async def test_memory_search_defaults_to_requester_memory_and_requires_scope(db_session):
    owner = Contact(whatsapp_id="2348044444444@c.us", display_name="Fabian")
    db_session.add(owner)
    await db_session.flush()
    await MemoryService(db_session).upsert_memory(owner.id, display_name="Fabian", projects="AU MCP beta")

    result = await ToolDispatcherService(db_session).execute(
        "memory.search",
        {"query": "AU MCP"},
        context=ToolExecutionContext(permission="owner", requested_by_contact_id=owner.id),
    )
    assert result["result"]["contact_id"] == owner.id
    assert result["result"]["contact_resolution"] == {"status": "requester", "contact_id": owner.id}
    assert result["result"]["profile"]["projects"] == "AU MCP beta"

    with pytest.raises(ValueError, match="requires contact or requested_by_contact_id"):
        await ToolDispatcherService(db_session).execute(
            "memory.search",
            {"query": "AU MCP"},
            context=ToolExecutionContext(permission="owner"),
        )


@pytest.mark.asyncio
async def test_admin_permission_cannot_execute_owner_tool(db_session):
    dispatcher = ToolDispatcherService(db_session)
    with pytest.raises(ValueError, match="permission denied"):
        await dispatcher.execute(
            "whatsapp.send_message",
            {"target": "Amanda", "text": "hello"},
            context=ToolExecutionContext(permission="admin"),
        )
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_disabled_tool_is_denied_before_side_effect(db_session):
    dispatcher = ToolDispatcherService(db_session)
    await dispatcher.registry.set_enabled("whatsapp.send_message", False)

    with pytest.raises(ValueError, match="disabled"):
        await dispatcher.execute(
            "whatsapp.send_message",
            {"target": "Amanda", "text": "hello"},
            context=ToolExecutionContext(permission="owner"),
        )
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


@pytest.mark.asyncio
async def test_unknown_extra_and_out_of_range_arguments_are_rejected(db_session):
    dispatcher = ToolDispatcherService(db_session)
    with pytest.raises(ValueError, match="unknown tool argument"):
        await dispatcher.execute(
            "whatsapp.send_message",
            {"target": "Amanda", "text": "hello", "bypass": True},
            context=ToolExecutionContext(permission="owner"),
        )

    with pytest.raises(ValueError, match="above maximum"):
        await dispatcher.execute(
            "whatsapp.find_contact",
            {"query": "Amanda", "limit": 21},
            context=ToolExecutionContext(permission="owner"),
        )

    with pytest.raises(ValueError, match="not registered"):
        await dispatcher.execute(
            "au.reason",
            {"prompt": "do something"},
            context=ToolExecutionContext(permission="owner"),
        )


@pytest.mark.asyncio
async def test_nonimplemented_registered_tool_cannot_fake_success(db_session):
    dispatcher = ToolDispatcherService(db_session)
    with pytest.raises(ValueError, match="no executable adapter"):
        await dispatcher.execute(
            "task.create",
            {
                "action": "whatsapp.send_message",
                "scheduled_for": "2026-08-25T09:00:00+01:00",
                "timezone": "Africa/Lagos",
                "arguments": {},
            },
            context=ToolExecutionContext(permission="owner"),
        )

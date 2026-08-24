from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.models.scheduled_action import ScheduledAction
from app.models.schema import Contact
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
async def test_unknown_or_extra_arguments_are_rejected(db_session):
    dispatcher = ToolDispatcherService(db_session)
    with pytest.raises(ValueError, match="unknown tool argument"):
        await dispatcher.execute(
            "whatsapp.send_message",
            {"target": "Amanda", "text": "hello", "bypass": True},
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
            "memory.search",
            {"query": "Amanda"},
            context=ToolExecutionContext(permission="owner"),
        )

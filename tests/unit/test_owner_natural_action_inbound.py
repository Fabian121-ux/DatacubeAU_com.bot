from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.api.inbound import _owner_action_idempotency_key, _plan_owner_natural_action
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AdminAccount, Contact


@pytest.mark.asyncio
async def test_owner_from_me_instruction_creates_durable_scheduled_action(db_session, monkeypatch):
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id="2348000000001@c.us",
        role="primary_admin",
        permission_level="owner",
        is_primary=True,
        is_enabled=True,
    )
    amanda = Contact(
        whatsapp_id="2348000000002@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        normalized_phone="2348000000002",
    )
    db_session.add_all([owner, amanda])
    await db_session.flush()

    event = {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": "OWNER-ACTION-1",
            "chatId": "2348000000001@c.us",
            "from": "2348000000001@c.us",
            "fromMe": True,
            "body": "@Zina message Amanda Christabel tomorrow at 9am and tell her the document is ready",
        },
    }

    import app.services.natural_action_planner_service as planner_module

    fixed_now = datetime(2026, 8, 24, 19, 0, tzinfo=ZoneInfo("Africa/Lagos"))
    monkeypatch.setattr(planner_module, "utcnow", lambda: fixed_now)

    result = await _plan_owner_natural_action(
        db_session,
        event=event,
        message_id="OWNER-ACTION-1",
        request_id="OWNER-ACTION-1",
    )
    await db_session.commit()

    assert result is not None
    assert result.get("error") is None
    action = (await db_session.execute(select(ScheduledAction))).scalar_one()
    assert action.action_type == "whatsapp.send_message"
    assert action.target_contact_id == amanda.id
    assert action.target_chat_id == amanda.whatsapp_id
    assert action.payload_json == {"text": "the document is ready"}
    assert action.scheduled_for.astimezone(ZoneInfo("Africa/Lagos")).hour == 9
    assert action.idempotency_key == "owner-natural-action:default:2348000000001@c.us:OWNER-ACTION-1"


@pytest.mark.asyncio
async def test_non_admin_from_me_instruction_is_denied(db_session, monkeypatch):
    amanda = Contact(
        whatsapp_id="2348000000002@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
    )
    db_session.add(amanda)
    await db_session.flush()

    event = {
        "event": "message",
        "session": "default",
        "payload": {
            "id": "OWNER-ACTION-DENIED",
            "chatId": "2348999999999@c.us",
            "from": "2348999999999@c.us",
            "fromMe": True,
            "body": "message Amanda Christabel tomorrow at 9am and tell her hello",
        },
    }

    import app.services.natural_action_planner_service as planner_module

    fixed_now = datetime(2026, 8, 24, 19, 0, tzinfo=ZoneInfo("Africa/Lagos"))
    monkeypatch.setattr(planner_module, "utcnow", lambda: fixed_now)

    result = await _plan_owner_natural_action(
        db_session,
        event=event,
        message_id="OWNER-ACTION-DENIED",
        request_id="OWNER-ACTION-DENIED",
    )

    assert result == {"error": "owner authorization failed"}
    assert (await db_session.execute(select(ScheduledAction))).scalars().all() == []


def test_owner_action_idempotency_is_shared_by_message_event_variants():
    payload = {"id": "OWNER-SAME", "chatId": "2348000000001@c.us"}
    message_event = {"event": "message", "session": "default", "payload": payload}
    message_any_event = {"event": "message.any", "session": "default", "payload": payload}

    assert _owner_action_idempotency_key(message_event, payload) == _owner_action_idempotency_key(
        message_any_event, payload
    )

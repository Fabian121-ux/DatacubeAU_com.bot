from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.models.scheduled_action import ScheduledAction
from app.services.conversation_export_service import ConversationExportService


class _ScalarRows:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _Result:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return _ScalarRows(self._rows)


class _RecordingSession:
    def __init__(self, result_sets):
        self.result_sets = list(result_sets)
        self.statements = []

    async def execute(self, statement):
        self.statements.append(statement)
        return _Result(self.result_sets.pop(0))


def _action(*, action_id: int, status: str, scheduled_for: datetime, updated_at: datetime) -> ScheduledAction:
    return ScheduledAction(
        id=action_id,
        action_type="whatsapp.send_message",
        target_contact_id=77,
        target_chat_id="2348011111111@c.us",
        payload_json={"text": f"message-{action_id}"},
        timezone="Africa/Lagos",
        scheduled_for=scheduled_for,
        status=status,
        is_enabled=status not in {"completed", "cancelled"},
        retry_count=0,
        max_retries=3,
        idempotency_key=f"action-{action_id}",
        created_at=updated_at,
        updated_at=updated_at,
    )


@pytest.mark.asyncio
async def test_scheduled_action_export_selects_active_before_recent_inactive_history():
    now = datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)
    active = _action(
        action_id=900,
        status="scheduled",
        scheduled_for=now + timedelta(days=1),
        updated_at=now - timedelta(days=30),
    )
    recent_completed = [
        _action(
            action_id=index,
            status="completed",
            scheduled_for=now - timedelta(days=1),
            updated_at=now - timedelta(minutes=index),
        )
        for index in range(1, 50)
    ]
    session = _RecordingSession([[active], recent_completed])
    service = ConversationExportService(session)

    rows = await service._scheduled_actions(77)

    assert len(rows) == 50
    assert rows[0]["id"] == 900
    assert rows[0]["status"] == "scheduled"
    first_sql = str(session.statements[0])
    second_sql = str(session.statements[1])
    assert "scheduled_actions.status IN" in first_sql
    assert "scheduled_actions.status NOT IN" in second_sql

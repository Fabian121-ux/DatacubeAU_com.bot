from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.conversation_analysis_service import ConversationAnalysisService
from app.services.conversation_export_service import ConversationExportService


def test_commitments_deduplicate_resend_delivery_events_by_logical_queue_message():
    base = datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)
    messages = [
        {
            "id": "outbound_queue:55:delivery:1001",
            "direction": "outbound",
            "text": "I will send the proposal tomorrow.",
            "created_at": base,
        },
        {
            "id": "outbound_queue:55:delivery:1002",
            "direction": "outbound",
            "text": "I will send the proposal tomorrow.",
            "created_at": base + timedelta(minutes=5),
        },
        {
            "id": 77,
            "direction": "outbound",
            "text": "I will call Amanda later.",
            "created_at": base + timedelta(minutes=10),
        },
    ]

    result = ConversationAnalysisService._commitments(messages)

    assert [item["text"] for item in result] == [
        "I will send the proposal tomorrow",
        "I will call Amanda later",
    ]
    assert [item["source_message_id"] for item in result] == [
        "outbound_queue:55:delivery:1002",
        77,
    ]


def test_commitment_cap_retains_newest_clauses_and_keeps_chronological_order():
    base = datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)
    messages = [
        {
            "id": index + 1,
            "direction": "outbound",
            "text": f"I will complete task {index}.",
            "created_at": base + timedelta(minutes=index),
        }
        for index in range(30)
    ]

    result = ConversationAnalysisService._commitments(messages)

    assert len(result) == ConversationAnalysisService.MAX_COMMITMENTS
    assert result[0]["text"] == "I will complete task 5"
    assert result[-1]["text"] == "I will complete task 29"


def test_recurring_topic_preserves_leading_dot_for_dotnet_identity():
    summaries = [
        {"id": 1, "topics": [".NET"]},
        {"id": 2, "topics": [".NET"]},
    ]
    messages = [
        {"id": 10, "direction": "inbound", "text": ".NET migration starts tomorrow."},
        {"id": 11, "direction": "outbound", "text": "I prefer .NET for this service."},
        {"id": 12, "direction": "inbound", "text": "Net income increased this quarter."},
    ]

    result = ConversationAnalysisService._recurring_topics(summaries, messages)

    assert result[0]["topic"] == ".NET"
    assert result[0]["dm_message_count"] == 2
    assert result[0]["source_message_ids"] == [10, 11]


def test_executing_scheduled_action_is_active_in_export_and_analysis():
    assert "executing" in ConversationExportService.ACTIVE_ACTION_STATUSES
    assert "pending" not in ConversationExportService.ACTIVE_ACTION_STATUSES
    assert "retrying" not in ConversationExportService.ACTIVE_ACTION_STATUSES

    action = {
        "id": 51,
        "action_type": "whatsapp.send_message",
        "status": "executing",
        "scheduled_for": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
        "timezone": "Africa/Lagos",
        "source_message_id": 99,
    }

    dates = ConversationAnalysisService._important_dates([action])
    follow_ups = ConversationAnalysisService._recommended_follow_ups([], [action])

    assert dates[0]["scheduled_action_id"] == 51
    assert dates[0]["status"] == "executing"
    assert follow_ups[0]["source_scheduled_action_id"] == 51
    assert follow_ups[0]["status"] == "executing"


class _BoundedExporter:
    def __init__(self, *, after: datetime, before: datetime):
        self.after = after
        self.before = before

    async def export(self, **kwargs):
        assert kwargs["limit"] == 50
        assert kwargs["after"] == self.after
        assert kwargs["before"] == self.before
        return {
            "schema_version": "zina.chat.v1",
            "contact": {"contact_id": 77, "display_name": "Amanda"},
            "conversation": {
                "message_count": 0,
                "limit": 50,
                "after": self.after,
                "before": self.before,
                "window": {"oldest_at": None, "newest_at": None},
                "messages": [],
            },
            "memory": {"summaries": []},
            "open_loops": [],
            "zina_activity": {"scheduled_actions": []},
        }


@pytest.mark.asyncio
async def test_analysis_window_preserves_requested_bounds_even_when_no_messages_match():
    after = datetime(2026, 8, 1, 0, 0, tzinfo=timezone.utc)
    before = datetime(2026, 8, 2, 0, 0, tzinfo=timezone.utc)
    service = ConversationAnalysisService(object())
    service.exporter = _BoundedExporter(after=after, before=before)

    payload = await service.analyze(
        contact_reference="Amanda",
        limit=50,
        after=after,
        before=before,
    )

    assert payload["window"] == {
        "limit": 50,
        "after": after,
        "before": before,
        "oldest_at": None,
        "newest_at": None,
    }

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.services.conversation_analysis_service import ConversationAnalysisService


@pytest.mark.asyncio
async def test_analysis_composes_zina_chat_export_without_llm():
    export = {
        "schema_version": "zina.chat.v1",
        "contact": {"contact_id": 77, "display_name": "Amanda Christabel"},
        "conversation": {
            "message_count": 4,
            "window": {
                "oldest_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
                "newest_at": datetime(2026, 8, 20, 8, 10, tzinfo=timezone.utc),
            },
            "messages": [
                {
                    "id": 10,
                    "direction": "inbound",
                    "text": "Did you send the proposal?",
                    "created_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
                },
                {
                    "id": "delivery:21",
                    "direction": "outbound",
                    "text": "I will send the proposal today.",
                    "created_at": datetime(2026, 8, 20, 8, 2, tzinfo=timezone.utc),
                },
                {
                    "id": 12,
                    "direction": "inbound",
                    "text": "Will you also send the invoice?",
                    "created_at": datetime(2026, 8, 20, 8, 5, tzinfo=timezone.utc),
                },
                {
                    "id": "delivery:22",
                    "direction": "outbound",
                    "text": "Let me check the invoice first.",
                    "created_at": datetime(2026, 8, 20, 8, 10, tzinfo=timezone.utc),
                },
            ],
        },
        "memory": {
            "summaries": [
                {"id": 31, "topics": ["Proposal", "Invoice"]},
                {"id": 32, "topics": ["proposal"]},
            ]
        },
        "open_loops": [
            {
                "id": 41,
                "type": "question",
                "text": "Did you send the proposal?",
                "source_message_id": 10,
                "last_message_id": 10,
                "updated_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
            }
        ],
        "zina_activity": {
            "scheduled_actions": [
                {
                    "id": 51,
                    "action_type": "whatsapp.send_message",
                    "status": "scheduled",
                    "scheduled_for": datetime(2026, 8, 25, 9, 0, tzinfo=timezone.utc),
                    "timezone": "Africa/Lagos",
                    "source_message_id": 99,
                }
            ]
        },
    }

    analysis = ConversationAnalysisService.derive(export)

    assert analysis["status"] == "generated"
    assert analysis["method"] == "deterministic_evidence_projection"
    assert analysis["unresolved_matters"][0]["open_loop_id"] == 41
    assert [item["source_message_id"] for item in analysis["explicit_commitments"]] == ["delivery:21", "delivery:22"]
    assert analysis["explicit_commitments"][0]["text"] == "I will send the proposal today"
    assert analysis["recurring_topics"][0] == {
        "topic": "Proposal",
        "summary_count": 2,
        "dm_message_count": 2,
        "source_summary_ids": [31, 32],
        "source_message_ids": [10, "delivery:21"],
    }
    assert analysis["important_dates"][0]["scheduled_action_id"] == 51
    kinds = [item["kind"] for item in analysis["recommended_follow_ups"]]
    assert kinds == ["open_loop", "scheduled_action"]
    assert "No LLM is used" in analysis["limitations"][-1]


def test_analysis_does_not_invent_commitments_from_inbound_or_non_commitment_outbound_text():
    export = {
        "conversation": {
            "messages": [
                {"id": 1, "direction": "inbound", "text": "I will send the file."},
                {"id": 2, "direction": "outbound", "text": "Thanks, noted."},
                {"id": 3, "direction": "inbound", "text": "Will you send it tomorrow?"},
                {"id": 4, "direction": "outbound", "text": "Let me know if you need anything."},
            ]
        },
        "memory": {"summaries": []},
        "open_loops": [],
        "zina_activity": {"scheduled_actions": []},
    }

    analysis = ConversationAnalysisService.derive(export)

    assert analysis["explicit_commitments"] == []
    assert analysis["recurring_topics"] == []
    assert analysis["recommended_follow_ups"] == []


def test_commitments_accept_curly_apostrophe_and_split_multiple_sentence_bounded_clauses():
    messages = [
        {
            "id": "delivery:1",
            "direction": "outbound",
            "text": "I’ll send it tomorrow. How is your family? I can call you later; I promise to update Amanda.",
            "created_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
        }
    ]

    commitments = ConversationAnalysisService._commitments(messages)

    assert [item["text"] for item in commitments] == [
        "I’ll send it tomorrow",
        "I can call you later",
        "I promise to update Amanda",
    ]
    assert all(item["source_message_id"] == "delivery:1" for item in commitments)


def test_recurring_topics_require_two_summary_mentions_and_two_dm_message_matches():
    summaries = [
        {"id": 1, "topics": ["Proposal", "Group Only"]},
        {"id": 2, "topics": ["Proposal", "Group Only"]},
        {"id": 3, "topics": ["Invoice"]},
    ]
    messages = [
        {"id": 10, "direction": "inbound", "text": "The proposal is ready."},
        {"id": 11, "direction": "outbound", "text": "I reviewed the proposal."},
        {"id": 12, "direction": "inbound", "text": "The invoice arrived."},
    ]

    topics = ConversationAnalysisService._recurring_topics(summaries, messages)

    assert [item["topic"] for item in topics] == ["Proposal"]
    assert topics[0]["source_message_ids"] == [10, 11]


def test_recurring_topics_return_all_bounded_summary_evidence_ids():
    summaries = [{"id": index, "topics": ["Proposal"]} for index in range(1, 16)]
    messages = [
        {"id": 101, "direction": "inbound", "text": "Proposal update"},
        {"id": 102, "direction": "outbound", "text": "Proposal received"},
    ]

    topics = ConversationAnalysisService._recurring_topics(summaries, messages)

    assert topics[0]["summary_count"] == 15
    assert topics[0]["source_summary_ids"] == list(range(1, 16))


def test_important_dates_filter_active_actions_sort_by_schedule_then_apply_cap():
    base = datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc)
    completed = [
        {
            "id": f"completed-{index}",
            "action_type": "whatsapp.send_message",
            "status": "completed",
            "scheduled_for": base - timedelta(days=index + 1),
        }
        for index in range(30)
    ]
    active = [
        {
            "id": 200,
            "action_type": "whatsapp.send_message",
            "status": "scheduled",
            "scheduled_for": base + timedelta(hours=2),
        },
        {
            "id": 199,
            "action_type": "whatsapp.send_message",
            "status": "queued",
            "scheduled_for": base + timedelta(hours=1),
        },
    ]

    dates = ConversationAnalysisService._important_dates(completed + active)

    assert [item["scheduled_action_id"] for item in dates] == [199, 200]


class _FakeExporter:
    async def export(self, **kwargs):
        assert kwargs["contact_reference"] == "Amanda"
        assert kwargs["limit"] == 50
        assert kwargs["requested_by_contact_id"] == 91
        return {
            "schema_version": "zina.chat.v1",
            "contact": {"contact_id": 77, "display_name": "Amanda"},
            "conversation": {
                "message_count": 1,
                "window": {"oldest_at": None, "newest_at": None},
                "messages": [],
            },
            "memory": {"summaries": []},
            "open_loops": [],
            "zina_activity": {"scheduled_actions": []},
        }


@pytest.mark.asyncio
async def test_analyze_preserves_export_provenance_and_declares_no_llm():
    service = ConversationAnalysisService(object())
    service.exporter = _FakeExporter()

    payload = await service.analyze(contact_reference="Amanda", limit=50, requested_by_contact_id=91)

    assert payload["schema_version"] == "zina.chat.analysis.v1"
    assert payload["conversation_schema_version"] == "zina.chat.v1"
    assert payload["contact"]["contact_id"] == 77
    assert payload["provenance"] == {
        "conversation_export": "zina.chat.v1",
        "analysis_method": "deterministic_evidence_projection",
        "llm_used": False,
        "source_ids_are_required": True,
    }

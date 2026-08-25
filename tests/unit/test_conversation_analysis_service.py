from __future__ import annotations

from datetime import datetime, timezone

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
        "source_summary_ids": [31, 32],
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

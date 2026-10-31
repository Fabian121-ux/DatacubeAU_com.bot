from __future__ import annotations

from datetime import datetime, timezone

from app.services.conversation_analysis_service import ConversationAnalysisService


def test_commitment_prefix_requires_complete_modal_phrase():
    messages = [
        {
            "id": 1,
            "direction": "outbound",
            "text": "I willfully rejected the request. I shallower-tested the branch.",
            "created_at": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        }
    ]

    assert ConversationAnalysisService._commitments(messages) == []


def test_long_message_evidence_is_sliced_around_late_commitment():
    prefix = "context " * 80
    commitment = "I will send the signed proposal tomorrow"
    messages = [
        {
            "id": 2,
            "direction": "outbound",
            "text": prefix + commitment + ".",
            "created_at": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        }
    ]

    result = ConversationAnalysisService._commitments(messages)

    assert result[0]["text"] == commitment
    assert commitment in result[0]["evidence_text"]
    assert len(result[0]["evidence_text"]) <= 400


def test_quoted_first_person_speech_is_not_attributed_to_fabian():
    messages = [
        {
            "id": 3,
            "direction": "outbound",
            "text": "Amanda said, “I will send the invoice tomorrow.” I will review it when it arrives.",
            "created_at": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        }
    ]

    result = ConversationAnalysisService._commitments(messages)

    assert [item["text"] for item in result] == ["I will review it when it arrives"]


def test_commitment_sentence_detection_preserves_urls_and_dotted_abbreviations():
    messages = [
        {
            "id": 4,
            "direction": "outbound",
            "text": "I will review example.com tomorrow. I will call at 3 p.m. tomorrow; I can update you later.",
            "created_at": datetime(2026, 8, 25, 8, 0, tzinfo=timezone.utc),
        }
    ]

    result = ConversationAnalysisService._commitments(messages)

    assert [item["text"] for item in result] == [
        "I will review example.com tomorrow",
        "I will call at 3 p.m. tomorrow",
        "I can update you later",
    ]


def test_recurring_topic_counts_each_summary_once_even_with_duplicate_labels():
    summaries = [
        {"id": 1, "topics": ["Proposal", "proposal", "PROPOSAL"]},
        {"id": 2, "topics": ["Proposal"]},
    ]
    messages = [
        {"id": 10, "direction": "inbound", "text": "Proposal update"},
        {"id": 11, "direction": "outbound", "text": "Proposal received"},
    ]

    result = ConversationAnalysisService._recurring_topics(summaries, messages)

    assert result[0]["summary_count"] == 2
    assert result[0]["source_summary_ids"] == [1, 2]


def test_resends_do_not_count_as_independent_topic_corroboration():
    summaries = [
        {"id": 1, "topics": ["Proposal"]},
        {"id": 2, "topics": ["Proposal"]},
    ]
    resend_only = [
        {
            "id": "outbound_queue:55:delivery:1001",
            "direction": "outbound",
            "text": "Proposal update",
        },
        {
            "id": "outbound_queue:55:delivery:1002",
            "direction": "outbound",
            "text": "Proposal update",
        },
    ]

    assert ConversationAnalysisService._recurring_topics(summaries, resend_only) == []

    with_distinct_message = resend_only + [
        {"id": 77, "direction": "inbound", "text": "Any proposal news?"}
    ]
    result = ConversationAnalysisService._recurring_topics(summaries, with_distinct_message)

    assert result[0]["dm_message_count"] == 2
    assert result[0]["source_message_ids"] == ["outbound_queue:55:delivery:1001", 77]

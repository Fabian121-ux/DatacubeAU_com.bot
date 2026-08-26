from __future__ import annotations

from app.services.conversation_analysis_service import ConversationAnalysisService


def test_commitments_reject_negated_i_can_forms():
    messages = [
        {"id": 1, "direction": "outbound", "text": "I can't send the file."},
        {"id": 2, "direction": "outbound", "text": "I can’t send the file."},
        {"id": 3, "direction": "outbound", "text": "I cannot send the file."},
        {"id": 4, "direction": "outbound", "text": "I can send the file tomorrow."},
    ]

    commitments = ConversationAnalysisService._commitments(messages)

    assert [item["source_message_id"] for item in commitments] == [4]
    assert commitments[0]["text"] == "I can send the file tomorrow"


def test_topic_matching_preserves_cplusplus_and_csharp_as_distinct_tokens():
    assert ConversationAnalysisService._topic_matches_text("C++", "We discussed C++ templates today.") is True
    assert ConversationAnalysisService._topic_matches_text("C++", "We discussed C# records today.") is False
    assert ConversationAnalysisService._topic_matches_text("C#", "We discussed C# records today.") is True
    assert ConversationAnalysisService._topic_matches_text("C#", "We discussed C++ templates today.") is False


def test_recurring_symbol_topics_require_matching_dm_evidence():
    summaries = [
        {"id": 1, "topics": ["C++", "C#"]},
        {"id": 2, "topics": ["C++", "C#"]},
    ]
    messages = [
        {"id": 10, "direction": "inbound", "text": "C# records are useful."},
        {"id": 11, "direction": "outbound", "text": "I reviewed the C# code."},
    ]

    topics = ConversationAnalysisService._recurring_topics(summaries, messages)

    assert [item["topic"] for item in topics] == ["C#"]
    assert topics[0]["source_message_ids"] == [10, 11]

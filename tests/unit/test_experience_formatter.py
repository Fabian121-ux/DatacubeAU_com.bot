from __future__ import annotations

from app.core.experience_formatter import WhatsAppExperienceFormatter, format_whatsapp_quote, memory_context_indicators


def test_source_indicator_badges() -> None:
    formatter = WhatsAppExperienceFormatter()

    assert formatter.source_badge("Rule") == "Rule"
    assert formatter.source_badge("FAQ") == "FAQ"
    assert formatter.source_badge("KB") == "Knowledge"
    assert formatter.source_badge("Memory") == "Memory"
    assert formatter.source_badge("Cache") == "Cache"
    assert formatter.source_badge("AI") == "Global Chat"
    assert formatter.source_badge("Internet") == "Internet"
    assert formatter.source_badge("Giphy") == "Giphy"
    assert formatter.source_badge("Memory + Timeline") == "Memory + Timeline"


def test_context_indicators_prefix_reply_when_memory_exists() -> None:
    formatter = WhatsAppExperienceFormatter()
    reply = formatter.format_reply(
        "How is that going?",
        source="Memory",
        context_indicators=["Welcome back Kingsley.", "Last time we discussed cybersecurity internships."],
    )

    assert reply.startswith("*Zina*")
    assert "Welcome back Kingsley.\nLast time we discussed cybersecurity internships." in reply
    assert "Source: Memory" in reply
    assert "How is that going?" in reply


def test_signature_style_can_be_disabled_for_legacy_shape() -> None:
    formatter = WhatsAppExperienceFormatter()
    reply = formatter.format_reply(
        "Datacube AU is active.",
        source="Rule",
        context_indicators=[],
        enable_signature_style=False,
    )

    assert reply == "Source: Rule\n\nDatacube AU is active."


def test_format_whatsapp_quote_single_line() -> None:
    assert format_whatsapp_quote("Message text") == "> Message text"


def test_format_whatsapp_quote_multiline_paragraphs() -> None:
    assert format_whatsapp_quote("Good morning, Daniel.\n\nIt looks like it may rain today.") == (
        "> Good morning, Daniel.\n\n"
        "> It looks like it may rain today."
    )


def test_format_whatsapp_quote_preserves_blank_lines() -> None:
    assert format_whatsapp_quote("First line\n\n\nSecond line") == "> First line\n\n\n> Second line"


def test_format_whatsapp_quote_does_not_duplicate_existing_marker() -> None:
    assert format_whatsapp_quote("> Already quoted\n\nNext line") == "> Already quoted\n\n> Next line"


def test_format_reply_can_quote_only_the_body() -> None:
    formatter = WhatsAppExperienceFormatter()
    reply = formatter.format_reply(
        "ZinaX is part of Fabian's AI ecosystem.",
        source="Identity",
        show_source=False,
        quote_body=True,
    )

    assert reply == "*Zina*\n\n> ZinaX is part of Fabian's AI ecosystem."


def test_memory_context_indicators_only_from_used_memory_diagnostics() -> None:
    assert memory_context_indicators({"context_used": True, "context_indicators": ["Welcome back Kingsley."]}) == ["Welcome back Kingsley."]
    assert memory_context_indicators({"context_indicators": ["Welcome back Kingsley."]}) == []
    assert memory_context_indicators({"retrieved_items": 0}) == []
    assert memory_context_indicators(None) == []


def test_formatter_splits_large_text_walls() -> None:
    formatter = WhatsAppExperienceFormatter()
    long_text = " ".join(["This is a sentence about Zina and the WhatsApp experience."] * 20)

    formatted = formatter.format_reply(long_text, source="AI", context_indicators=[])

    assert formatted.startswith("*Zina*")
    assert "Source: Global Chat" in formatted
    assert "\n\n" in formatted


def test_reply_template_supports_next_step() -> None:
    formatter = WhatsAppExperienceFormatter()
    formatted = formatter.format_reply(
        "Your deployment issue is likely related to container logs.",
        source="KB",
        next_step="Check the Docker container logs.",
    )

    assert "Your deployment issue is likely related to container logs." in formatted
    assert "*Next Step*\n\nCheck the Docker container logs." in formatted


def test_formatter_sections_bullets_and_numbering() -> None:
    formatter = WhatsAppExperienceFormatter()

    assert formatter.section("Focus", "Memory Engine") == "Focus\n\nMemory Engine"
    assert formatter.bullets(["Item 1", "Item 2"]) == "• Item 1\n• Item 2"
    assert formatter.numbered(["First", "Second"]) == "1. First\n2. Second"


def test_project_card_template() -> None:
    formatter = WhatsAppExperienceFormatter()
    card = formatter.project_card(
        name="Zina",
        status="Active Development",
        focus="Memory Engine",
        next_priority="Owner Commands",
    )

    assert card == (
        "*Zina*\n\n"
        "Status:\nActive Development\n\n"
        "Focus:\nMemory Engine\n\n"
        "Next Priority:\nOwner Commands"
    )


def test_status_card_template() -> None:
    formatter = WhatsAppExperienceFormatter()
    card = formatter.status_card(
        api="Online ✅",
        database="Connected ✅",
        waha="Connected ✅",
        ai="Disabled ⚪",
    )

    assert card == (
        "*System Status*\n\n"
        "API:\nOnline ✅\n\n"
        "Database:\nConnected ✅\n\n"
        "WAHA:\nConnected ✅\n\n"
        "AI:\nDisabled ⚪"
    )


def test_typing_delay_calculation() -> None:
    formatter = WhatsAppExperienceFormatter()

    assert formatter.typing_delay_seconds("short", enabled=False) == 0
    assert formatter.typing_delay_seconds("/global on", is_command=True) == 0
    assert formatter.typing_delay_seconds("short", min_seconds=1, max_seconds=6) == 2
    assert formatter.typing_delay_seconds("x" * 1200, min_seconds=1, max_seconds=6) == 6
    assert formatter.typing_delay_seconds("details", min_seconds=1, max_seconds=6, mode="detailed") == 6


def test_thinking_indicators_are_stage_specific() -> None:
    formatter = WhatsAppExperienceFormatter()

    assert formatter.thinking_indicator("memory") == "Checking memory..."
    assert formatter.thinking_indicator("knowledge") == "Searching knowledge..."
    assert formatter.thinking_indicator("internet") == "Searching internet..."
    assert formatter.thinking_indicator("thinking") == "Generating response..."

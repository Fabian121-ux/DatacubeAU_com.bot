import pytest
from app.core.whatsapp_formatter import (
    format_quote,
    format_inline_code,
    format_quoted_inline_code,
    format_whatsapp_response,
    WhatsAppMessageFormat,
    get_applied_format_mode
)

@pytest.fixture(scope="session", autouse=True)
def setup_test_database():
    pass


def test_format_quote_single_line():
    assert format_quote("This is an important message.") == "> This is an important message."

def test_format_quote_multiple_paragraphs():
    text = "First paragraph.\n\nSecond paragraph."
    expected = "> First paragraph.\n\n> Second paragraph."
    assert format_quote(text) == expected

def test_format_quote_already_quoted():
    text = "> Already quoted"
    assert format_quote(text) == text

def test_format_quote_empty():
    assert format_quote("") == ""
    assert format_quote("   ") == "   "

def test_format_inline_code_basic():
    assert format_inline_code("/help") == "`/help`"

def test_format_inline_code_already_coded():
    assert format_inline_code("`/help`") == "`/help`"

def test_format_inline_code_multiline_skips():
    text = "multiline\ncode"
    assert format_inline_code(text) == text

def test_format_inline_code_triple_backticks_skips():
    text = "```python\nprint('hello')\n```"
    assert format_inline_code(text) == text

def test_format_inline_code_unmatched_backticks_skips():
    text = "missing ` backtick"
    assert format_inline_code(text) == text

def test_format_quoted_inline_code():
    text = "Use /help to view all commands."
    expected = "> `Use /help to view all commands.`"
    assert format_quoted_inline_code(text) == expected

def test_automatic_mode_greetings():
    assert get_applied_format_mode("Hello, Daniel. How can I help you today?", "automatic") == WhatsAppMessageFormat.STANDARD.value
    assert get_applied_format_mode("Good morning!", "automatic") == WhatsAppMessageFormat.STANDARD.value

def test_automatic_mode_long_paragraphs():
    text = "Love can mean deep affection, care, commitment, or emotional connection depending on the context. " * 15
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.STANDARD.value

def test_automatic_mode_short_instructions():
    # Only command -> QUOTE_INLINE_CODE
    text = "/help"
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE_INLINE_CODE.value
    
    # "Use command..." -> QUOTE_INLINE_CODE
    text = "Use /help to view all available commands."
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE_INLINE_CODE.value
    
    # "Run..." -> QUOTE_INLINE_CODE
    text = "Run docker compose up -d --build"
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE_INLINE_CODE.value
    
    # Env var setting -> QUOTE_INLINE_CODE
    text = "Set LOCAL_LLM_ENABLED=true"
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE_INLINE_CODE.value

def test_automatic_mode_warnings():
    text = "Your administrator account has been disabled."
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE.value
    
    text = "The FAQ synchronization completed successfully."
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.QUOTE.value

def test_automatic_mode_standard_with_inline_commands():
    # If the text is standard but contains technical fragments, they are wrapped.
    # The mode evaluated is STANDARD.
    text = "You can use /help to see commands."
    formatted = format_whatsapp_response(text, "automatic")
    assert formatted == "You can use `/help` to see commands."

def test_preserve_existing_whatsapp_formatting():
    # Should not touch text with existing formatting
    text = "This is *bold* and _italic_."
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.STANDARD.value
    assert format_whatsapp_response(text, "automatic") == text
    
    text = "Check out https://google.com"
    assert get_applied_format_mode(text, "automatic") == WhatsAppMessageFormat.STANDARD.value

def test_format_whatsapp_response_specific_mode():
    text = "Just a normal text"
    assert format_whatsapp_response(text, "quote") == "> Just a normal text"
    assert format_whatsapp_response(text, "inline_code") == "`Just a normal text`"
    assert format_whatsapp_response(text, "quote_inline_code") == "> `Just a normal text`"

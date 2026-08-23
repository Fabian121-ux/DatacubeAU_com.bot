import re
from enum import Enum

class WhatsAppMessageFormat(str, Enum):
    STANDARD = "standard"
    QUOTE = "quote"
    INLINE_CODE = "inline_code"
    QUOTE_INLINE_CODE = "quote_inline_code"
    AUTOMATIC = "automatic"

def format_quote(text: str) -> str:
    if not text or not text.strip():
        return text
    
    # Don't double quote
    if is_already_quoted(text):
        return text

    quoted_lines = []
    for line in text.splitlines():
        if not line.strip():
            quoted_lines.append("")
        else:
            quoted_lines.append(f"> {line.lstrip(' >')}")
    return "\n".join(quoted_lines)

def format_inline_code(text: str) -> str:
    if not text:
        return text
        
    text = text.strip()
    
    # Do not wrap multiline content
    if "\n" in text:
        return text
        
    # Do not double-wrap
    if text.startswith("`") and text.endswith("`"):
        return text
        
    # Check if there are triple backticks
    if "```" in text:
        return text
        
    # Unmatched backticks check
    if text.count("`") % 2 != 0:
        return text
        
    return f"`{text}`"

def format_quoted_inline_code(text: str) -> str:
    if not text:
        return text
        
    # Fallback if multiline (do not wrap in inline code, but quote it)
    if "\n" in text.strip():
        return format_quote(text)
        
    # Format inline code first, then quote it
    inline_coded = format_inline_code(text)
    return format_quote(inline_coded)

def is_already_quoted(text: str) -> bool:
    lines = [line for line in text.splitlines() if line.strip()]
    if not lines:
        return False
    return all(line.lstrip().startswith(">") for line in lines)

def has_existing_markup(text: str) -> bool:
    if "```" in text:
        return True
    if re.search(r"`[^`\n]+`", text):
        return True
    if is_already_quoted(text):
        return True
    # URL check
    if re.search(r"https?://|www\.", text, flags=re.IGNORECASE):
        return True
    # Unmatched backticks
    if text.count("`") % 2 != 0:
        return True
    # Bold, italic, strikethrough checking (approximate)
    if re.search(r"(^|\s)\*[^*]+\*(\s|$)", text):
        return True
    if re.search(r"(^|\s)_[^_]+_(\s|$)", text):
        return True
    if re.search(r"(^|\s)~[^~]+~(\s|$)", text):
        return True
    return False

def evaluate_automatic_mode(response: str) -> str:
    if not response or not response.strip():
        return WhatsAppMessageFormat.STANDARD.value
        
    stripped = response.strip()
    
    # 1. Check for multiline
    has_newlines = "\n" in stripped
    lines = [line for line in stripped.splitlines() if line.strip()]
    
    # 2. Existing markup
    if has_existing_markup(response):
        return WhatsAppMessageFormat.STANDARD.value
        
    normalized = response.lower().strip()
    
    # 3. Greetings & emotional conversation (keep standard)
    if normalized.startswith(("hi ", "hi.", "hi,", "hello", "good morning", "good afternoon", "good evening")):
        if len(normalized) < 160 and not has_newlines:
            return WhatsAppMessageFormat.STANDARD.value
            
    # 4. Long explanations, FAQ answers, Identity answers (keep standard)
    if len(stripped) > 900 or len(lines) > 5:
        return WhatsAppMessageFormat.STANDARD.value
        
    # 5. Short technical instructions -> QUOTE_INLINE_CODE
    if len(stripped) <= 160 and not has_newlines:
        is_technical = bool(
            re.search(r"(docker compose up|docker build|docker run|\bnpm run\b|npm install|git clone|git push)", normalized) or
            re.search(r"^(/help|/status|![a-z]+)", normalized) or
            re.search(r"\b[A-Z_]+=[^\s]+\b", stripped) or
            re.search(r"\b/[a-z0-9_/-]+\b", stripped) or
            re.search(r"(^Use \/[a-z]+|Run [a-z]+|Set [A-Z_]+|Open [a-z.-]+)", stripped)
        )
        if is_technical:
            if re.match(r"^(run|use|set|open|execute|type)\b", normalized) or re.match(r"^(/|!)[a-z]+(\s|$)", normalized) or re.match(r"^[a-z_]+=[^\s]+$", normalized):
                return WhatsAppMessageFormat.QUOTE_INLINE_CODE.value
                
            return WhatsAppMessageFormat.STANDARD.value

    # 6. Important warnings, summaries, admin notices -> QUOTE
    if len(stripped) <= 250 and not has_newlines:
        if re.search(r"\b(warning|error|failed|disabled|successfully|success|completed|back up|attention)\b", normalized):
            return WhatsAppMessageFormat.QUOTE.value

    return WhatsAppMessageFormat.STANDARD.value

def extract_and_format_inline_commands(text: str) -> str:
    """Helper to wrap commands/paths in backticks within standard text if not already wrapped."""
    if has_existing_markup(text):
        return text
    
    def repl(m):
        cmd = m.group(1)
        return f"`{cmd}`"
        
    formatted = re.sub(r"(?<!`)(/[a-z0-9_-]+|![a-z0-9_-]+)(?!`)", repl, text)
    formatted = re.sub(r"(?<!`)\b([A-Z][A-Z0-9_]+=[^\s.,]+)(?!`)", repl, formatted)
    
    return formatted

def get_applied_format_mode(response: str, mode: str) -> str:
    if not response:
        return WhatsAppMessageFormat.STANDARD.value
        
    mode = mode.lower().strip()
    if mode == WhatsAppMessageFormat.AUTOMATIC.value:
        return evaluate_automatic_mode(response)
    return mode

def format_whatsapp_response(response: str, mode: str) -> str:
    """
    Applies the WhatsApp response formatting.
    """
    if not response:
        return response
        
    applied_mode = get_applied_format_mode(response, mode)
        
    if applied_mode == WhatsAppMessageFormat.QUOTE.value:
        return format_quote(response)
    elif applied_mode == WhatsAppMessageFormat.INLINE_CODE.value:
        return format_inline_code(response)
    elif applied_mode == WhatsAppMessageFormat.QUOTE_INLINE_CODE.value:
        return format_quoted_inline_code(response)
    else:
        return extract_and_format_inline_commands(response)

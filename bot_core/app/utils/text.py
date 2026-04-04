import re
from typing import Iterable


_WHITESPACE_RE = re.compile(r"\s+")
_NON_WORD_RE = re.compile(r"[^\w\s]")


def normalize_text(text: str) -> str:
    value = text.lower().strip()
    value = _NON_WORD_RE.sub(" ", value)
    value = _WHITESPACE_RE.sub(" ", value)
    return value


def estimate_tokens(text: str) -> int:
    # Lightweight approximation to avoid tokenization overhead in V1.
    return max(1, len(text) // 4)


def is_greeting(text: str) -> bool:
    normalized = normalize_text(text)
    greetings = {
        "hi",
        "hello",
        "hey",
        "good morning",
        "good afternoon",
        "good evening",
    }
    return normalized in greetings


def looks_complex(text: str) -> bool:
    normalized = normalize_text(text)
    complex_markers = ("why", "how", "compare", "tradeoff", "architecture", "design", "root cause")
    if len(normalized.split()) >= 20:
        return True
    return any(marker in normalized for marker in complex_markers)


def has_any_keyword(text: str, keywords: Iterable[str]) -> bool:
    normalized = normalize_text(text)
    for keyword in keywords:
        if keyword and normalize_text(keyword) in normalized:
            return True
    return False


from __future__ import annotations

from enum import Enum
import re
from typing import Any


SOURCE_LABELS = {
    "Rule": "Rule",
    "FAQ": "FAQ",
    "KB": "Knowledge",
    "Knowledge Base": "Knowledge",
    "Knowledge": "Knowledge",
    "Timeline": "Timeline",
    "Memory": "Memory",
    "Cache": "Cache",
    "AI": "Global Chat",
    "Global Chat": "Global Chat",
    "Internet": "Internet",
    "Giphy": "Giphy",
    "Identity": "Identity",
    "Fallback": "Fallback",
}

SUPPORTED_PROJECTS = {"Datacube AU", "Zina", "ZinaX", "Moxiz Gateway"}


class ReplyMode(str, Enum):
    QUICK = "quick"
    NORMAL = "normal"
    DETAILED = "detailed"


from app.core.whatsapp_formatter import WhatsAppMessageFormat

class WhatsAppExperienceFormatter:
    """Formats user-visible replies without hiding full admin diagnostics."""

    max_paragraph_chars = 420
    max_reply_chars = 2800
    quick_reply_chars = 700
    detailed_reply_chars = 4200

    def format_reply(
        self,
        reply_text: str,
        *,
        source: str,
        context_indicators: list[str] | None = None,
        show_source: bool = True,
        show_context: bool = True,
        enable_signature_style: bool = True,
        mode: str = ReplyMode.NORMAL.value,
        next_step: str | None = None,
        whatsapp_format_mode: str = "standard",
    ) -> str:
        body = self.format_body(reply_text)
        from app.core.whatsapp_formatter import format_whatsapp_response
        body = format_whatsapp_response(body, whatsapp_format_mode)
        indicators = self._clean_indicators(context_indicators or []) if show_context else []
        if not enable_signature_style:
            return self._legacy_reply(
                body,
                source=source,
                indicators=indicators,
                show_source=show_source,
            )

        parts = ["*Zina*"]
        if indicators:
            parts.append("\n".join(indicators))

        answer_parts: list[str] = []
        if show_source:
            answer_parts.append(f"Source: {self.source_badge(source)}")
        if body:
            answer_parts.append(body)
        parts.append("\n\n".join(answer_parts))

        if next_step:
            parts.append(self._section("*Next Step*", self.format_body(next_step)))

        return self._limit_reply("\n\n".join(part for part in parts if part), mode)

    def _legacy_reply(
        self,
        body: str,
        *,
        source: str,
        indicators: list[str],
        show_source: bool,
    ) -> str:
        parts: list[str] = []
        if show_source:
            parts.append(f"Source: {self.source_badge(source)}")
        parts.append(body)
        return "\n\n".join(part for part in parts if part).strip()[: self.max_reply_chars]

    def source_badge(self, source: str | None) -> str:
        if source and "+" in source:
            parts = [part.strip() for part in source.split("+") if part.strip()]
            return " + ".join(SOURCE_LABELS.get(part, part) for part in parts)
        return SOURCE_LABELS.get(source or "", SOURCE_LABELS["Fallback"])

    def thinking_indicator(self, stage: str) -> str:
        stage_key = stage.strip().lower()
        if stage_key == "knowledge":
            return "Searching knowledge..."
        if stage_key == "memory":
            return "Checking memory..."
        if stage_key == "internet":
            return "Searching internet..."
        return "Generating response..."

    def format_body(self, text: str) -> str:
        cleaned = self._normalize_spacing(text)
        if not cleaned:
            return cleaned
        if self._already_structured(cleaned):
            return self._limit_large_paragraphs(cleaned)
        if len(cleaned) <= self.max_paragraph_chars:
            return cleaned
        return self._paragraphize(cleaned)

    def section(self, title: str, body: str) -> str:
        return self._section(title.strip(), self.format_body(body))

    def bullets(self, items: list[str]) -> str:
        return "\n".join(f"• {item.strip()}" for item in items if item.strip())

    def numbered(self, items: list[str]) -> str:
        return "\n".join(f"{index}. {item.strip()}" for index, item in enumerate(items, 1) if item.strip())

    def project_card(
        self,
        *,
        name: str,
        purpose: str = "",
        status: str = "",
        focus: str = "",
        next_priority: str = "",
        next_step: str = "",
    ) -> str:
        project_name = name.strip()
        lines = [f"*{project_name}*"]
        if purpose:
            lines.extend(["", "Purpose:", purpose.strip()])
        if status:
            lines.extend(["", "Status:", status.strip()])
        if focus:
            lines.extend(["", "Focus:", focus.strip()])
        next_value = next_priority or next_step
        if next_value:
            lines.extend(["", "Next Priority:", next_value.strip()])
        return "\n".join(lines)

    def status_card(
        self,
        *,
        title: str = "System Status",
        status: str = "",
        api: str = "",
        database: str = "",
        waha: str = "",
        ai: str = "",
        details: list[str] | None = None,
    ) -> str:
        lines = [f"*{title.strip()}*"]
        if status:
            lines.extend(["", "Status:", status.strip()])
        for label, value in (
            ("API", api),
            ("Database", database),
            ("WAHA", waha),
            ("AI", ai),
        ):
            if value:
                lines.extend(["", f"{label}:", value.strip()])
        if details:
            lines.extend(["", self.bullets(details)])
        return "\n".join(lines)

    def typing_delay_seconds(
        self,
        text: str,
        *,
        enabled: bool = True,
        min_seconds: float = 1.0,
        max_seconds: float = 6.0,
        mode: str = ReplyMode.NORMAL.value,
        is_command: bool = False,
    ) -> float:
        if not enabled or is_command:
            return 0.0
        lower = max(0.0, float(min_seconds))
        upper = max(lower, float(max_seconds))
        if upper == 0:
            return 0.0

        normalized_mode = self._reply_mode(mode)
        length = len(self._normalize_spacing(text))
        if normalized_mode == ReplyMode.QUICK:
            target = lower
        elif normalized_mode == ReplyMode.DETAILED:
            target = upper
        elif length <= 160:
            target = lower + min(1.0, upper - lower)
        elif length <= 900:
            target = lower + ((upper - lower) * 0.55)
        else:
            target = upper
        return round(min(upper, max(lower, target)), 2)

    @staticmethod
    def _clean_indicators(indicators: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for indicator in indicators:
            value = indicator.strip()
            if not value:
                continue
            if value not in seen:
                seen.add(value)
                cleaned.append(value)
        return cleaned[:3]

    @staticmethod
    def _section(title: str, body: str) -> str:
        clean_title = title.strip()
        clean_body = body.strip()
        if not clean_body:
            return clean_title
        return f"{clean_title}\n\n{clean_body}"

    @staticmethod
    def _normalize_spacing(text: str) -> str:
        lines = [line.rstrip() for line in text.strip().splitlines()]
        compact = "\n".join(lines)
        compact = re.sub(r"\n{3,}", "\n\n", compact)
        return compact.strip()

    @staticmethod
    def _already_structured(text: str) -> bool:
        return bool(
            bool(re.search(r"(^|\n)([-*•]|\d+\.)\s+", text))
            or bool(re.search(r"(^|\n)>\s*", text))
            or "\n\n" in text
            or re.search(r"^\*[^*]+\*", text)
            or re.search(r"^[\w\s]+:\n", text)
        )

    def _limit_large_paragraphs(self, text: str) -> str:
        paragraphs = text.split("\n\n")
        return "\n\n".join(self._paragraphize(paragraph) if len(paragraph) > self.max_paragraph_chars else paragraph for paragraph in paragraphs)

    def _paragraphize(self, text: str) -> str:
        sentences = re.split(r"(?<=[.!?])\s+", text)
        paragraphs: list[str] = []
        current = ""
        for sentence in sentences:
            if not sentence:
                continue
            candidate = f"{current} {sentence}".strip()
            if len(candidate) > self.max_paragraph_chars and current:
                paragraphs.append(current)
                current = sentence
            else:
                current = candidate
        if current:
            paragraphs.append(current)
        return "\n\n".join(paragraphs)

    def _limit_reply(self, text: str, mode: str) -> str:
        limit = self.max_reply_chars
        if self._reply_mode(mode) == ReplyMode.QUICK:
            limit = self.quick_reply_chars
        elif self._reply_mode(mode) == ReplyMode.DETAILED:
            limit = self.detailed_reply_chars
        return text.strip()[:limit]

    @staticmethod
    def _reply_mode(mode: str) -> ReplyMode:
        try:
            return ReplyMode(str(mode).strip().lower())
        except ValueError:
            return ReplyMode.NORMAL


def memory_context_indicators(memory_diagnostics: dict[str, Any] | None) -> list[str]:
    if not isinstance(memory_diagnostics, dict):
        return []
    if not memory_diagnostics.get("context_used"):
        return []
    indicators = memory_diagnostics.get("context_indicators")
    if isinstance(indicators, list):
        return [str(item) for item in indicators]
    return []

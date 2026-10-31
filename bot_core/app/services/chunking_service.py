from __future__ import annotations

from dataclasses import dataclass
import re

from app.utils.text import estimate_tokens


HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.+?)\s*$")


@dataclass(slots=True)
class TextChunk:
    chunk_index: int
    heading: str | None
    content: str
    token_estimate: int


class ChunkingService:
    def __init__(self, target_min: int = 500, target_max: int = 900, overlap: int = 120):
        self.target_min = target_min
        self.target_max = target_max
        self.overlap = overlap

    def chunk_text(self, raw_text: str) -> list[TextChunk]:
        sections = self._split_sections(raw_text)
        chunks: list[TextChunk] = []
        chunk_index = 0

        for heading, section_text in sections:
            for body in self._chunk_section(section_text):
                content = body.strip()
                if not content:
                    continue
                chunks.append(
                    TextChunk(
                        chunk_index=chunk_index,
                        heading=heading,
                        content=content,
                        token_estimate=estimate_tokens(content),
                    )
                )
                chunk_index += 1
        return chunks

    def _split_sections(self, raw_text: str) -> list[tuple[str | None, str]]:
        sections: list[tuple[str | None, str]] = []
        current_heading: str | None = None
        current_lines: list[str] = []

        for line in raw_text.splitlines():
            match = HEADING_RE.match(line)
            if match:
                if current_lines:
                    sections.append((current_heading, "\n".join(current_lines).strip()))
                    current_lines = []
                current_heading = match.group(2).strip()
                continue
            current_lines.append(line)

        if current_lines:
            sections.append((current_heading, "\n".join(current_lines).strip()))

        if not sections:
            return [(None, raw_text.strip())]
        return sections

    def _chunk_section(self, text: str) -> list[str]:
        if len(text) <= self.target_max:
            return [text]

        chunks: list[str] = []
        start = 0
        text_length = len(text)
        while start < text_length:
            end = min(start + self.target_max, text_length)
            if end < text_length and (end - start) >= self.target_min:
                break_at = max(
                    text.rfind("\n", start + self.target_min, end),
                    text.rfind(". ", start + self.target_min, end),
                    text.rfind(" ", start + self.target_min, end),
                )
                if break_at > start:
                    end = break_at + 1

            chunks.append(text[start:end].strip())
            if end >= text_length:
                break
            start = max(end - self.overlap, start + 1)

        return chunks

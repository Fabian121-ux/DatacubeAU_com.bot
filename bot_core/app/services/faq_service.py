import logging
import re
import difflib
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.schema import FAQEntry
from app.utils.text import normalize_text
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

# Pattern to capture Q & A structures in markdown
FAQ_PATTERN = re.compile(
    r"##?\s*Q:\s*(.*?)\n\s*A:\s*(.*?)(?=\n##?\s*Q:|$)",
    re.IGNORECASE | re.DOTALL
)


class FAQService:
    def __init__(self, session: AsyncSession):
        self.session = session

    def parse_faq_text(self, raw_text: str) -> list[tuple[str, str]]:
        pairs = []
        for match in FAQ_PATTERN.finditer(raw_text):
            q = match.group(1).strip()
            a = match.group(2).strip()
            if q and a:
                pairs.append((q, a))
        return pairs

    async def sync_faq_in_db(self, pairs: list[tuple[str, str]]) -> int:
        count = 0
        seen: set[str] = set()
        for question, answer in pairs:
            normalized = normalize_text(question)
            if normalized in seen:
                continue
            seen.add(normalized)
            now = utcnow()
            stmt = pg_insert(FAQEntry).values(
                question=question,
                normalized_question=normalized,
                answer=answer,
                is_enabled=True,
                created_at=now,
                updated_at=now,
            ).on_conflict_do_update(
                index_elements=[FAQEntry.normalized_question],
                set_={
                    "question": question,
                    "answer": answer,
                    "is_enabled": True,
                    "updated_at": now,
                },
            )
            await self.session.execute(stmt)
            count += 1

        await self.session.flush()
        logger.info(f"Synchronized {count} FAQ entries in database.")
        return count

    async def load_faq_from_file(self, file_path: str) -> int:
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"FAQ file {file_path} not found.")
            return 0
        try:
            raw = path.read_text(encoding="utf-8")
            pairs = self.parse_faq_text(raw)
            return await self.sync_faq_in_db(pairs)
        except Exception as exc:
            await self.session.rollback()
            logger.error(f"Failed to load FAQ from file {file_path}: {exc}", exc_info=True)
            return 0

    async def search_faq(self, query: str, threshold: float = 0.72) -> tuple[FAQEntry | None, float]:
        query_norm = normalize_text(query)
        if not query_norm.strip():
            return None, 0.0
        if self._is_greeting_or_too_short(query_norm):
            return None, 0.0

        stmt = select(FAQEntry).where(FAQEntry.is_enabled.is_(True))
        entries = (await self.session.execute(stmt)).scalars().all()

        best_entry = None
        best_score = 0.0

        for entry in entries:
            score = self.score_match(query_norm, entry.normalized_question)

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= threshold:
            return best_entry, best_score

        return None, best_score

    @classmethod
    def score_match(cls, query_norm: str, question_norm: str) -> float:
        if query_norm == question_norm:
            return 1.0
        if query_norm in question_norm or question_norm in query_norm:
            sequence_score = difflib.SequenceMatcher(None, query_norm, question_norm).ratio()
            if sequence_score >= 0.82:
                return min(1.0, sequence_score + 0.12)
        query_tokens = cls._keywords(query_norm)
        question_tokens = cls._keywords(question_norm)
        if not query_tokens or not question_tokens:
            return 0.0

        sequence_score = difflib.SequenceMatcher(None, query_norm, question_norm).ratio()
        overlap = query_tokens & question_tokens
        union = query_tokens | question_tokens
        jaccard_score = len(overlap) / len(union) if union else 0.0
        coverage_score = len(overlap) / min(len(query_tokens), len(question_tokens))
        order_bonus = 0.0
        if query_norm in question_norm or question_norm in query_norm:
            order_bonus = 0.12
        entity_bonus = 0.08 if overlap & {"fabian", "zina", "datacube", "zinax", "moxiz"} else 0.0

        score = (sequence_score * 0.35) + (jaccard_score * 0.25) + (coverage_score * 0.4)
        return min(1.0, score + order_bonus + entity_bonus)

    @staticmethod
    def _keywords(text_value: str) -> set[str]:
        stop_words = {
            "a",
            "an",
            "and",
            "are",
            "can",
            "do",
            "does",
            "for",
            "have",
            "how",
            "i",
            "is",
            "it",
            "me",
            "my",
            "of",
            "the",
            "to",
            "what",
            "when",
            "where",
            "who",
            "why",
            "you",
            "your",
        }
        return {word for word in re.findall(r"[a-z0-9]+", text_value) if word not in stop_words}

    @staticmethod
    def _is_greeting_or_too_short(query_norm: str) -> bool:
        if query_norm in {"hi", "hello", "hey", "yo", "good morning", "good afternoon", "good evening"}:
            return True
        words = query_norm.split()
        if len(words) <= 4 and words and words[0] in {"hi", "hello", "hey"}:
            return True
        return len([word for word in words if len(word) > 2]) == 0

import logging
import re
import difflib
from pathlib import Path
from sqlalchemy import select, delete
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
        # Clear existing
        await self.session.execute(delete(FAQEntry))
        
        count = 0
        seen: set[str] = set()
        for question, answer in pairs:
            normalized = normalize_text(question)
            if normalized in seen:
                continue
            seen.add(normalized)
            entry = FAQEntry(
                question=question,
                normalized_question=normalized,
                answer=answer,
                is_enabled=True,
                created_at=utcnow(),
                updated_at=utcnow()
            )
            self.session.add(entry)
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

    async def search_faq(self, query: str, threshold: float = 0.55) -> tuple[FAQEntry | None, float]:
        query_norm = normalize_text(query)
        if not query_norm.strip():
            return None, 0.0

        stmt = select(FAQEntry).where(FAQEntry.is_enabled.is_(True))
        entries = (await self.session.execute(stmt)).scalars().all()

        best_entry = None
        best_score = 0.0

        for entry in entries:
            # SequenceMatcher similarity ratio
            score = difflib.SequenceMatcher(None, query_norm, entry.normalized_question).ratio()
            # Also boost if the query contains the normalized question or vice-versa
            if query_norm in entry.normalized_question or entry.normalized_question in query_norm:
                score = max(score, 0.7)

            if score > best_score:
                best_score = score
                best_entry = entry

        if best_entry and best_score >= threshold:
            return best_entry, best_score

        return None, best_score

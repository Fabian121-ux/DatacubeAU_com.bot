from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.schema import FAQEntry
from app.services.faq_service import FAQService
from app.utils.text import normalize_text


FAQ_MARKDOWN = """# Core FAQ

## Q: Who are you?
A: Hi, I'm Zina.

## Q: What is Datacube AU?
A: Datacube AU is Fabian's WhatsApp assistant system.

## Q: Who are you?
A: Duplicate should be ignored.
"""


class FakeScalarResult:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return list(self._rows)


class FakeExecuteResult:
    def __init__(self, rows):
        self._rows = rows

    def scalars(self):
        return FakeScalarResult(self._rows)


class FakeFAQSession:
    def __init__(self):
        self.entries: list[FAQEntry] = []
        self.flushed = False
        self.rolled_back = False

    async def execute(self, statement):
        if statement.__class__.__name__ == "Delete":
            self.entries.clear()
        return FakeExecuteResult(self.entries)

    def add(self, entry):
        self.entries.append(entry)

    async def flush(self):
        self.flushed = True

    async def rollback(self):
        self.rolled_back = True


def test_parse_faq_text_reads_markdown_pairs() -> None:
    service = FAQService(None)  # type: ignore[arg-type]

    pairs = service.parse_faq_text(FAQ_MARKDOWN)

    assert pairs == [
        ("Who are you?", "Hi, I'm Zina."),
        ("What is Datacube AU?", "Datacube AU is Fabian's WhatsApp assistant system."),
        ("Who are you?", "Duplicate should be ignored."),
    ]


@pytest.mark.asyncio
async def test_sync_and_search_faq_with_fake_session() -> None:
    session = FakeFAQSession()
    service = FAQService(session)  # type: ignore[arg-type]

    count = await service.sync_faq_in_db(service.parse_faq_text(FAQ_MARKDOWN))
    entry, score = await service.search_faq("who are you")
    similar_entry, similar_score = await service.search_faq("what is datacube")
    missing_entry, missing_score = await service.search_faq("unrelated payroll", threshold=0.95)

    assert count == 2
    assert session.flushed is True
    assert entry is not None
    assert entry.answer == "Hi, I'm Zina."
    assert score >= 0.95
    assert similar_entry is not None
    assert similar_entry.question == "What is Datacube AU?"
    assert similar_score >= 0.55
    assert missing_entry is None
    assert missing_score < 0.95


@pytest.mark.asyncio
async def test_empty_faq_query_short_circuits_fake_session() -> None:
    session = FakeFAQSession()
    service = FAQService(session)  # type: ignore[arg-type]

    entry, score = await service.search_faq("")

    assert entry is None
    assert score == 0.0


@pytest.mark.asyncio
async def test_sync_faq_deduplicates_and_exact_lookup_works(db_session) -> None:
    service = FAQService(db_session)

    count = await service.sync_faq_in_db(service.parse_faq_text(FAQ_MARKDOWN))
    rows = (await db_session.execute(select(FAQEntry))).scalars().all()
    entry, score = await service.search_faq("Who are you?")

    assert count == 2
    assert len(rows) == 2
    assert entry is not None
    assert entry.normalized_question == normalize_text("Who are you?")
    assert entry.answer == "Hi, I'm Zina."
    assert score >= 0.99


@pytest.mark.asyncio
async def test_similar_faq_lookup_returns_best_match(db_session) -> None:
    service = FAQService(db_session)
    await service.sync_faq_in_db(
        [
            ("What services are offered?", "Fabian builds automation systems."),
            ("How can someone contact Fabian?", "Contact Fabian via WhatsApp or email."),
        ]
    )

    entry, score = await service.search_faq("what service do you offer")

    assert entry is not None
    assert entry.question == "What services are offered?"
    assert score >= 0.55


@pytest.mark.asyncio
async def test_missing_faq_returns_none_with_best_score(db_session) -> None:
    service = FAQService(db_session)
    await service.sync_faq_in_db([("Who are you?", "Hi, I'm Zina.")])

    entry, score = await service.search_faq("completely unrelated payroll question", threshold=0.85)
    empty_entry, empty_score = await service.search_faq("")

    assert entry is None
    assert 0.0 <= score < 0.85
    assert empty_entry is None
    assert empty_score == 0.0


@pytest.mark.asyncio
async def test_load_faq_from_file_syncs_database(db_session, tmp_path) -> None:
    path = tmp_path / "core_faq.md"
    path.write_text(FAQ_MARKDOWN, encoding="utf-8")
    service = FAQService(db_session)

    count = await service.load_faq_from_file(str(path))
    entry, _ = await service.search_faq("what is datacube au")

    assert count == 2
    assert entry is not None
    assert entry.answer == "Datacube AU is Fabian's WhatsApp assistant system."


@pytest.mark.asyncio
async def test_load_faq_missing_file_is_safe(db_session, tmp_path) -> None:
    service = FAQService(db_session)

    assert await service.load_faq_from_file(str(tmp_path / "missing.md")) == 0

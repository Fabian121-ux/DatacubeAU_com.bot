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
        self.candidates = []
        self.flushed = False
        self.rolled_back = False

    async def execute(self, statement):
        statement_text = str(statement)
        if statement.__class__.__name__ == "Delete":
            self.entries.clear()
        if "faq_import_candidates" in statement_text:
            return FakeExecuteResult(self.candidates)
        return FakeExecuteResult(self.entries)

    def add(self, entry):
        if entry.__class__.__name__ == "FAQImportCandidate":
            entry.id = len(self.candidates) + 1
            self.candidates.append(entry)
            return
        entry.id = len(self.entries) + 1
        self.entries.append(entry)

    async def flush(self):
        self.flushed = True

    async def rollback(self):
        self.rolled_back = True

    async def get(self, model, row_id):
        rows = self.candidates if model.__name__ == "FAQImportCandidate" else self.entries
        return next((row for row in rows if row.id == row_id), None)


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
async def test_semantic_faq_lookup_handles_paraphrases_and_abbreviations() -> None:
    session = FakeFAQSession()
    service = FAQService(session)  # type: ignore[arg-type]

    await service.sync_faq_in_db([("What is your name?", "I'm Zina.")])

    entry, score = await service.search_faq("What's ur name?")
    identity_entry, identity_score = await service.search_faq("Tell me about yourself.")

    assert entry is not None
    assert entry.answer == "I'm Zina."
    assert score >= 0.72
    assert identity_entry is not None
    assert identity_score >= 0.68


@pytest.mark.asyncio
async def test_sync_faq_is_idempotent_for_help_command_variations() -> None:
    session = FakeFAQSession()
    service = FAQService(session)  # type: ignore[arg-type]
    answer = "Available commands: /help, /status, /mode."

    count = await service.sync_faq_in_db([("help", answer), ("/help", answer), ("commands", answer)])

    assert count == 1
    assert len(session.entries) == 1
    assert session.entries[0].intent == "command_help"
    assert set(session.entries[0].question_variations) >= {"help", "/help", "commands"}


@pytest.mark.asyncio
async def test_import_candidates_require_approval_before_publish() -> None:
    session = FakeFAQSession()
    service = FAQService(session)  # type: ignore[arg-type]
    raw = "Who is Fabian?\n\nFabian is an AI systems builder."

    result = await service.import_candidates(raw, source_name="test")
    missing, _ = await service.search_faq("who is fabian", track_usage=False)
    entry = await service.approve_candidate(1)
    approved, score = await service.search_faq("who is fabian", track_usage=False)

    assert result["created"] == 1
    assert missing is None
    assert entry.question == "Who is Fabian?"
    assert approved is not None
    assert approved.answer == "Fabian is an AI systems builder."
    assert score >= 0.72


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

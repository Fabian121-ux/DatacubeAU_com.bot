import asyncio
import tempfile
from pathlib import Path
import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.faq_service import FAQService
from app.models.schema import FAQEntry

pytestmark = pytest.mark.asyncio

async def test_first_core_faq_bootstrap(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.\n\nQ2?\n\nA2.")
        path = f.name

    try:
        service = FAQService(db_session)
        report = await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        assert report["active_entries"] == 2
        assert report["created"] == 2
        
        stmt = select(FAQEntry).where(FAQEntry.source_id == "core_faq")
        entries = (await db_session.execute(stmt)).scalars().all()
        assert len(entries) == 2
    finally:
        Path(path).unlink(missing_ok=True)


async def test_repeated_bootstrap(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.\n\nQ2?\n\nA2.")
        path = f.name

    try:
        service = FAQService(db_session)
        report1 = await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        assert report1["created"] == 2

        report2 = await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        assert report2["created"] == 0
        assert report2["unchanged"] == 2
        assert report2["updated"] == 0
        assert report2["active_entries"] == 2
        
        stmt = select(FAQEntry).where(FAQEntry.source_id == "core_faq")
        entries = (await db_session.execute(stmt)).scalars().all()
        assert len(entries) == 2
    finally:
        Path(path).unlink(missing_ok=True)


async def test_concurrent_bootstrap_attempts(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.")
        path = f.name

    try:
        service = FAQService(db_session)
        
        async def run_bootstrap():
            async with db_session.begin_nested():
                await db_session.execute(text("SELECT pg_advisory_xact_lock(42000002)"))
                report = await service.load_faq_report_from_file(path)
                return report

        res1, res2 = await asyncio.gather(run_bootstrap(), run_bootstrap())
        
        created_total = res1["created"] + res2["created"]
        unchanged_total = res1["unchanged"] + res2["unchanged"]
        
        assert created_total == 1
        assert unchanged_total == 1
    finally:
        Path(path).unlink(missing_ok=True)


async def test_core_entry_update(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.")
        path = f.name

    try:
        service = FAQService(db_session)
        await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        with open(path, "w") as f:
            f.write("Q1?\n\nA1_updated.")
            
        report = await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        assert report["updated"] == 1
        assert report["unchanged"] == 0
        
        stmt = select(FAQEntry).where(FAQEntry.source_id == "core_faq")
        entry = (await db_session.execute(stmt)).scalars().first()
        assert entry.answer == "A1_updated."
    finally:
        Path(path).unlink(missing_ok=True)


async def test_manual_faq_preservation(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.")
        path = f.name

    try:
        service = FAQService(db_session)
        custom_entry = FAQEntry(
            source_id="manual",
            source_name="Manual Entry",
            question="Q1?",
            normalized_question=service.build_payload("Q1?", "A1.").normalized_question,
            dedupe_key=service.build_payload("Q1?", "A1.").dedupe_key,
            answer="Manual Answer",
            is_enabled=True,
            sync_status="manual"
        )
        db_session.add(custom_entry)
        await db_session.commit()
        
        report = await service.load_faq_report_from_file(path)
        await db_session.commit()
        
        assert report["conflicted"] == 1
        assert report["created"] == 0
        
        stmt = select(FAQEntry)
        entries = (await db_session.execute(stmt)).scalars().all()
        assert len(entries) == 1
        assert entries[0].source_id == "manual"
        assert entries[0].answer == "Manual Answer"
    finally:
        Path(path).unlink(missing_ok=True)


async def test_rollback_after_failure(db_session: AsyncSession):
    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as f:
        f.write("Q1?\n\nA1.")
        path = f.name

    try:
        service = FAQService(db_session)
        original_method = service.replace_source_entries_report
        
        async def mock_replace(*args, **kwargs):
            await original_method(*args, **kwargs)
            raise RuntimeError("Injected failure")
            
        service.replace_source_entries_report = mock_replace
        
        report = await service.load_faq_report_from_file(path)
        assert report == {}
        
        stmt = select(FAQEntry).where(FAQEntry.source_id == "core_faq")
        entries = (await db_session.execute(stmt)).scalars().all()
        assert len(entries) == 0
    finally:
        Path(path).unlink(missing_ok=True)

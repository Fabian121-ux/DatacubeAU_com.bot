from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.models.schema import Contact
from app.services.contact_sync_service import ContactSyncService
from app.services.owner_management_command_service import OwnerManagementCommandService
from app.services.waha_client import WAHAClient, WahaClientError


@pytest.mark.asyncio
async def test_waha_contact_page_rejects_dictionary_without_person_identifier(monkeypatch):
    client = WAHAClient()
    monkeypatch.setattr(client, "_request", AsyncMock(return_value=[{}]))
    try:
        with pytest.raises(WahaClientError, match="malformed contact entry"):
            await client.get_contacts(session_name="default")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_explicit_unsaved_status_clears_stale_address_book_name(db_session):
    contact = Contact(
        whatsapp_id="2348012345678@c.us",
        contact_name="Old Saved Name",
        push_name="Profile Name",
        identity_json={"is_saved_contact": True},
    )
    db_session.add(contact)
    await db_session.flush()

    outcome, _ = await ContactSyncService(db_session, waha=object())._sync_one(
        {
            "id": "2348012345678@s.whatsapp.net",
            "name": "Generic WAHA Name",
            "pushName": "Profile Name",
            "isMyContact": False,
        },
        sync_at=datetime.now(timezone.utc),
    )
    await db_session.refresh(contact)

    assert outcome == "updated"
    assert contact.contact_name is None
    assert contact.push_name == "Profile Name"
    assert contact.identity_json["is_saved_contact"] is False
    assert contact.identity_json["contact_name"] is None
    assert OwnerManagementCommandService._is_saved(contact) is False


@pytest.mark.asyncio
async def test_nameless_saved_contact_list_uses_neutral_label(db_session):
    contact = Contact(
        whatsapp_id="2348099999999@c.us",
        normalized_phone="2348099999999",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db_session.add(contact)
    await db_session.flush()

    rendered = await OwnerManagementCommandService(db_session)._contact_list("saved 20")

    assert "Unknown — 2348099999999" in rendered
    assert "Unsaved — 2348099999999" not in rendered


class _BareLidWaha:
    async def get_contacts(self, **kwargs):
        offset = int(kwargs.get("offset", 0))
        if offset == 0:
            return [{"id": "777777777777@lid", "isMyContact": True}]
        return []


@pytest.mark.asyncio
async def test_unmapped_bare_lid_suppresses_unsafe_absence_reconciliation(db_session):
    saved = Contact(
        whatsapp_id="2348088888888@c.us",
        contact_name="Still Saved",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": datetime.now(timezone.utc).isoformat(),
        },
    )
    db_session.add(saved)
    await db_session.commit()

    result = await ContactSyncService(db_session, waha=_BareLidWaha()).sync()
    await db_session.refresh(saved)

    assert result["fetched"] == 1
    assert saved.contact_name == "Still Saved"
    assert saved.identity_json["is_saved_contact"] is True


@pytest.mark.asyncio
async def test_contact_sync_advisory_lock_serializes_authoritative_scans():
    database_url = os.environ.get(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/datacube_bot_test",
    )
    engine = create_async_engine(database_url, pool_pre_ping=True)
    Session = async_sessionmaker(bind=engine, expire_on_commit=False)
    try:
        async with Session() as first, Session() as second:
            await ContactSyncService(first, waha=object())._acquire_sync_lock()
            acquired_while_first_holds = (
                await second.execute(
                    text("SELECT pg_try_advisory_xact_lock(:key)"),
                    {"key": ContactSyncService.SYNC_ADVISORY_LOCK_KEY},
                )
            ).scalar_one()
            assert acquired_while_first_holds is False

            await first.rollback()
            acquired_after_release = (
                await second.execute(
                    text("SELECT pg_try_advisory_xact_lock(:key)"),
                    {"key": ContactSyncService.SYNC_ADVISORY_LOCK_KEY},
                )
            ).scalar_one()
            assert acquired_after_release is True
            await second.rollback()
    finally:
        await engine.dispose()

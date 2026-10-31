from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest

from app.models.schema import Contact
from app.services.contact_sync_service import ContactSyncService
from app.services.owner_management_command_service import OwnerManagementCommandService
from app.services.waha_client import WAHAClient, WahaClientError


@pytest.mark.asyncio
async def test_waha_contacts_rejects_unrecognized_success_payload_before_empty_scan_reconciliation(monkeypatch):
    client = WAHAClient()
    monkeypatch.setattr(client, "_request", AsyncMock(return_value={"ok": True, "unexpected": []}))
    try:
        with pytest.raises(WahaClientError, match="unrecognized response shape"):
            await client.get_contacts(session_name="default")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_waha_contacts_rejects_malformed_entries_in_otherwise_valid_page(monkeypatch):
    client = WAHAClient()
    monkeypatch.setattr(
        client,
        "_request",
        AsyncMock(return_value=[{"id": "2348011111111@c.us"}, "not-a-contact"]),
    )
    try:
        with pytest.raises(WahaClientError, match="malformed contact entry"):
            await client.get_contacts(session_name="default")
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_older_absence_reconciliation_cannot_demote_newer_saved_evidence(db_session):
    newer = datetime.now(timezone.utc)
    older = newer - timedelta(minutes=5)
    contact = Contact(
        whatsapp_id="2348022222222@c.us",
        contact_name="Amanda",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": newer.isoformat(),
        },
    )
    db_session.add(contact)
    await db_session.flush()

    updated = await ContactSyncService(db_session, waha=object())._reconcile_absent_saved_contacts(
        set(),
        sync_at=older,
    )
    await db_session.refresh(contact)

    assert updated == 0
    assert contact.contact_name == "Amanda"
    assert contact.identity_json["is_saved_contact"] is True
    assert OwnerManagementCommandService._is_saved(contact) is True


@pytest.mark.asyncio
async def test_older_contact_page_cannot_overwrite_newer_saved_evidence(db_session):
    newer = datetime.now(timezone.utc)
    older = newer - timedelta(minutes=5)
    contact = Contact(
        whatsapp_id="2348033333333@c.us",
        contact_name="Current Name",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": newer.isoformat(),
        },
    )
    db_session.add(contact)
    await db_session.flush()

    outcome, _ = await ContactSyncService(db_session, waha=object())._sync_one(
        {
            "id": "2348033333333@s.whatsapp.net",
            "name": "Stale Name",
            "isMyContact": False,
        },
        sync_at=older,
    )
    await db_session.refresh(contact)

    assert outcome == "skipped"
    assert contact.contact_name == "Current Name"
    assert contact.identity_json["is_saved_contact"] is True

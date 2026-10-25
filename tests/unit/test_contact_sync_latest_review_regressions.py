from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import event

from app.models.schema import Contact
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
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

@pytest.mark.asyncio
@pytest.mark.parametrize("existing_contact", [True, False])
async def test_contact_sync_takes_mapping_lock_before_any_contact_flush(db_session, existing_contact):
    contact = None
    if existing_contact:
        # The sync will dirty ordinary Contact fields before filling in chat_id.
        # AsyncSession.execute() autoflushes those changes unless the mapping lock is
        # acquired first, which would invert the final dispatch fence's lock order.
        contact = Contact(
            whatsapp_id="2348044444444@c.us",
            display_name="Previous Name",
            contact_name="Previous Name",
        )
        db_session.add(contact)
        await db_session.flush()

    statements = []

    def capture_sql(conn, cursor, statement, parameters, context, executemany):
        normalized = " ".join(statement.lower().split())
        if "pg_advisory_xact_lock" in normalized and "hashtext" in normalized:
            statements.append("mapping_lock")
        elif normalized.startswith("update contacts") or normalized.startswith("insert into contacts"):
            statements.append("contact_write")

    engine = db_session.bind.sync_engine
    event.listen(engine, "before_cursor_execute", capture_sql)
    try:
        outcome, _ = await ContactSyncService(db_session, waha=object())._sync_one(
            {
                "id": "2348044444444@s.whatsapp.net",
                "name": "Amanda",
                "isMyContact": True,
            },
            sync_at=datetime.now(timezone.utc),
        )
    finally:
        event.remove(engine, "before_cursor_execute", capture_sql)

    assert outcome == ("updated" if existing_contact else "created")
    assert "mapping_lock" in statements
    assert "contact_write" in statements
    assert statements.index("mapping_lock") < statements.index("contact_write"), (
        "ContactSyncService must acquire the exact-chat advisory lock before ORM "
        "autoflush can take a Contact row lock"
    )
    if contact is not None:
        await db_session.refresh(contact)
        assert contact.chat_id == "2348044444444@c.us"


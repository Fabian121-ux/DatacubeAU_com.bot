from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.schema import Contact
from app.services.contact_sync_service import ContactSyncService
from app.services.owner_management_command_service import OwnerManagementCommandService


class _FakeWAHA:
    def __init__(self, pages):
        self.pages = list(pages)

    async def get_contacts(self, session_name=None, *, limit=500, offset=0):
        return self.pages.pop(0) if self.pages else []


@pytest.mark.asyncio
async def test_full_contact_sync_marks_removed_saved_contact_unsaved(db_session):
    contact = Contact(
        whatsapp_id="2348012345678@c.us",
        contact_name="Amanda Christabel",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-24T10:00:00+00:00",
        },
    )
    db_session.add(contact)
    await db_session.flush()

    # An empty first page is a complete WAHA address-book scan: absence is now
    # explicit evidence that the previously saved contact has been removed.
    result = await ContactSyncService(db_session, waha=_FakeWAHA([[]])).sync()
    await db_session.refresh(contact)

    assert result["updated"] == 1
    assert contact.contact_name is None
    assert contact.identity_json["is_saved_contact"] is False
    assert contact.identity_json["saved_contact_reconciled_reason"] == "absent_from_full_waha_contact_scan"
    assert OwnerManagementCommandService._is_saved(contact) is False


@pytest.mark.asyncio
async def test_explicit_waha_unsaved_state_demotes_existing_contact_without_deleting_identity(db_session):
    contact = Contact(
        whatsapp_id="2348099999999@c.us",
        contact_name="Old Saved Name",
        normalized_phone="2348099999999",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-24T10:00:00+00:00",
        },
    )
    db_session.add(contact)
    await db_session.flush()

    await ContactSyncService(
        db_session,
        waha=_FakeWAHA(
            [[
                {
                    "id": "2348099999999@s.whatsapp.net",
                    "pushName": "Mandy",
                    "isMyContact": False,
                }
            ]]
        ),
    ).sync()
    await db_session.refresh(contact)

    # The Contact row remains authoritative for the person, but stale address-book
    # name evidence is cleared when WAHA explicitly says the number is not saved.
    assert contact.contact_name is None
    assert contact.push_name == "Mandy"
    assert contact.normalized_phone == "2348099999999"
    assert contact.identity_json["is_saved_contact"] is False
    assert OwnerManagementCommandService._is_saved(contact) is False

    rows = (await db_session.execute(select(Contact))).scalars().all()
    assert rows == [contact]

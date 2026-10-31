from __future__ import annotations

import pytest

from app.models.schema import Contact
from app.services.contact_sync_service import ContactSyncService
from app.services.owner_management_command_service import OwnerManagementCommandService


class _FakeWAHA:
    def __init__(self, pages):
        self.pages = list(pages)

    async def get_contacts(self, session_name=None, *, limit=500, offset=0):
        return self.pages.pop(0) if self.pages else []


@pytest.mark.asyncio
async def test_inbound_identity_refresh_cannot_block_complete_scan_removal_reconciliation(db_session):
    contact = Contact(
        whatsapp_id="2348012345678@c.us",
        contact_name="Amanda Christabel",
        waha_contact_id="2348012345678@s.whatsapp.net",
        identity_json={"push_name": "Amanda"},  # simulates inbound replacement of sync JSON
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ContactSyncService(db_session, waha=_FakeWAHA([[]])).sync()
    await db_session.refresh(contact)

    assert result["updated"] == 1
    assert contact.contact_name is None
    assert contact.identity_json["is_saved_contact"] is False
    assert OwnerManagementCommandService._is_saved(contact) is False


@pytest.mark.asyncio
async def test_bare_lid_for_existing_saved_contact_is_seen_and_not_demoted(db_session):
    contact = Contact(
        whatsapp_id="2348022222222@c.us",
        contact_name="Lid Friend",
        waha_participant_id="123456789@lid",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-24T10:00:00+00:00",
        },
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ContactSyncService(
        db_session,
        waha=_FakeWAHA([[{"id": "123456789@lid", "isMyContact": True}]]),
    ).sync()
    await db_session.refresh(contact)

    assert result["updated"] == 1
    assert contact.identity_json["is_saved_contact"] is True
    assert OwnerManagementCommandService._is_saved(contact) is True


@pytest.mark.asyncio
async def test_explicit_saved_true_without_address_book_name_is_still_saved(db_session):
    await ContactSyncService(
        db_session,
        waha=_FakeWAHA(
            [[
                {
                    "id": "2348033333333@s.whatsapp.net",
                    "isMyContact": True,
                }
            ]]
        ),
    ).sync()

    from sqlalchemy import select

    contact = (
        await db_session.execute(
            select(Contact).where(Contact.whatsapp_id == "2348033333333@c.us")
        )
    ).scalar_one()
    assert contact.contact_name is None
    assert contact.identity_json["is_saved_contact"] is True
    assert OwnerManagementCommandService._is_saved(contact) is True


@pytest.mark.asyncio
async def test_unknown_legacy_saved_status_preserves_existing_true_marker(db_session):
    contact = Contact(
        whatsapp_id="2348044444444@c.us",
        waha_contact_id="2348044444444@s.whatsapp.net",
        identity_json={
            "is_saved_contact": True,
            "saved_contact_synced_at": "2026-08-24T10:00:00+00:00",
        },
    )
    db_session.add(contact)
    await db_session.flush()

    await ContactSyncService(
        db_session,
        waha=_FakeWAHA([[{"id": "2348044444444@s.whatsapp.net", "pushName": "Legacy"}]]),
    ).sync()
    await db_session.refresh(contact)

    assert contact.identity_json["is_saved_contact"] is True
    assert OwnerManagementCommandService._is_saved(contact) is True


@pytest.mark.asyncio
async def test_lid_to_pn_mapping_records_all_aliases_before_absence_reconciliation(db_session):
    contact = Contact(
        whatsapp_id="555555555@lid",
        waha_participant_id="555555555@lid",
        normalized_phone="2348055555555",
        contact_name="Mapped Friend",
        identity_json={"is_saved_contact": True},
    )
    db_session.add(contact)
    await db_session.flush()

    await ContactSyncService(
        db_session,
        waha=_FakeWAHA(
            [[
                {
                    "id": "555555555@lid",
                    "pn": "2348055555555@s.whatsapp.net",
                    "isMyContact": True,
                }
            ]]
        ),
    ).sync()
    await db_session.refresh(contact)

    assert contact.identity_json["is_saved_contact"] is True
    assert OwnerManagementCommandService._is_saved(contact) is True

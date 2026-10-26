from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models.schema import Contact
from app.services.contact_intelligence_service import ContactIntelligenceService
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
from app.services.contact_sync_service import ContactSyncService
from app.utils.time import utcnow


class _FakeWAHA:
    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = []

    async def get_contacts(self, session_name=None, *, limit=500, offset=0):
        self.calls.append({"session_name": session_name, "limit": limit, "offset": offset})
        return self.pages.pop(0) if self.pages else []


@pytest.mark.asyncio
async def test_sync_creates_saved_contact_and_makes_name_resolvable(db_session):
    waha = _FakeWAHA(
        [[
            {
                "id": "2348011111111@s.whatsapp.net",
                "name": "Amanda Christabel",
                "pushName": "Mandy",
            }
        ]]
    )

    result = await ContactSyncService(db_session, waha=waha).sync()

    assert result == {"fetched": 1, "created": 1, "updated": 0, "skipped": 0}
    contact = (await db_session.execute(select(Contact))).scalar_one()
    assert contact.whatsapp_id == "2348011111111@c.us"
    assert contact.contact_name == "Amanda Christabel"
    assert contact.push_name == "Mandy"
    assert contact.normalized_phone == "2348011111111"
    assert contact.identity_source == "waha_contact_sync"
    assert contact.identity_json["aliases"] == ["Amanda Christabel", "Mandy"]

    resolved = await ContactIntelligenceService(db_session).resolve("Amanda Christabel")
    assert resolved["status"] == "resolved"
    assert resolved["match"]["contact_id"] == contact.id


@pytest.mark.asyncio
async def test_sync_updates_existing_contact_without_overwriting_verified_display_name(db_session):
    contact = Contact(
        whatsapp_id="2348022222222@c.us",
        display_name="Amanda C.",
        contact_name="Old Name",
        normalized_phone="2348022222222",
        is_name_verified=True,
        identity_json={"aliases": ["Amanda"]},
    )
    db_session.add(contact)
    await db_session.flush()

    waha = _FakeWAHA(
        [[
            {
                "id": "2348022222222@s.whatsapp.net",
                "name": "Amanda Christabel",
                "pushName": "Mandy",
                "lid": "123456789@lid",
            }
        ]]
    )

    result = await ContactSyncService(db_session, waha=waha).sync()

    assert result["updated"] == 1
    await db_session.refresh(contact)
    assert contact.display_name == "Amanda C."
    assert contact.contact_name == "Amanda Christabel"
    assert contact.waha_contact_id == "2348022222222@s.whatsapp.net"
    assert contact.waha_participant_id == "123456789@lid"
    assert contact.identity_json["aliases"] == ["Amanda", "Amanda Christabel", "Mandy"]


@pytest.mark.asyncio
async def test_lid_contact_requires_phone_identity_before_creating_person_row(db_session):
    waha = _FakeWAHA(
        [[
            {"id": "123456789@lid", "name": "Amanda"},
            {
                "id": "987654321@lid",
                "pn": "2348033333333@s.whatsapp.net",
                "name": "Christabel",
            },
        ]]
    )

    result = await ContactSyncService(db_session, waha=waha).sync()

    assert result == {"fetched": 2, "created": 1, "updated": 0, "skipped": 1}
    contact = (await db_session.execute(select(Contact))).scalar_one()
    assert contact.whatsapp_id == "2348033333333@c.us"
    assert contact.waha_contact_id == "987654321@lid"
    assert contact.waha_participant_id == "987654321@lid"
    assert contact.normalized_phone == "2348033333333"


@pytest.mark.asyncio
async def test_sync_skips_non_person_contacts(db_session):
    waha = _FakeWAHA(
        [[
            {"id": "120363000000000000@g.us", "name": "Project Group"},
            {"id": "status@broadcast"},
            {"id": "120363123456789@newsletter", "name": "Channel"},
        ]]
    )

    result = await ContactSyncService(db_session, waha=waha).sync()

    assert result == {"fetched": 3, "created": 0, "updated": 0, "skipped": 3}
    assert (await db_session.execute(select(Contact))).scalars().all() == []

@pytest.mark.asyncio
async def test_sync_acquires_chat_mapping_lock_before_contact_row_lock(db_session, monkeypatch):
    exact_chat_id = "2348044444444@c.us"
    contact = Contact(
        whatsapp_id=exact_chat_id,
        chat_id=None,
        normalized_phone="2348044444444",
        identity_json={"is_saved_contact": True},
    )
    db_session.add(contact)
    await db_session.commit()  # Release the seed INSERT's row lock before measuring _sync_one.

    operations = []
    original_lock = ContactMessagingConsentService.lock_exact_chat_mapping
    original_find = ContactSyncService._find_existing

    async def tracked_lock(session, chat_id):
        operations.append(("mapping_lock", chat_id))
        await original_lock(session, chat_id)

    async def tracked_find(service, **kwargs):
        operation = "contact_lookup_for_update" if kwargs.get("for_update", True) else "contact_lookup_unlocked"
        operations.append((operation, None))
        return await original_find(service, **kwargs)

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "lock_exact_chat_mapping",
        staticmethod(tracked_lock),
    )
    monkeypatch.setattr(ContactSyncService, "_find_existing", tracked_find)

    service = ContactSyncService(
        db_session,
        waha=_FakeWAHA([]),
    )
    outcome, _ = await service._sync_one(
        {
            "id": "2348044444444@s.whatsapp.net",
            "name": "Amanda Christabel",
            "isMyContact": True,
        },
        sync_at=utcnow(),
    )

    assert outcome == "updated"
    assert operations == [
        ("contact_lookup_unlocked", None),
        ("mapping_lock", exact_chat_id),
        ("contact_lookup_for_update", None),
    ]

@pytest.mark.asyncio
async def test_sync_does_not_take_chat_mapping_lock_for_already_mapped_contact(db_session, monkeypatch):
    exact_chat_id = "2348055555555@c.us"
    contact = Contact(
        whatsapp_id=exact_chat_id,
        chat_id=exact_chat_id,
        normalized_phone="2348055555555",
        identity_json={"is_saved_contact": True},
    )
    db_session.add(contact)
    await db_session.commit()

    operations = []
    original_lock = ContactMessagingConsentService.lock_exact_chat_mapping
    original_find = ContactSyncService._find_existing

    async def tracked_lock(session, chat_id):
        operations.append(("mapping_lock", chat_id))
        await original_lock(session, chat_id)

    async def tracked_find(service, **kwargs):
        operation = "contact_lookup_for_update" if kwargs.get("for_update", True) else "contact_lookup_unlocked"
        operations.append((operation, None))
        return await original_find(service, **kwargs)

    monkeypatch.setattr(
        ContactMessagingConsentService,
        "lock_exact_chat_mapping",
        staticmethod(tracked_lock),
    )
    monkeypatch.setattr(ContactSyncService, "_find_existing", tracked_find)

    service = ContactSyncService(db_session, waha=_FakeWAHA([]))
    outcome, _ = await service._sync_one(
        {
            "id": "2348055555555@s.whatsapp.net",
            "name": "Already Mapped Contact",
            "isMyContact": True,
        },
        sync_at=utcnow(),
    )

    assert outcome == "updated"
    assert operations == [
        ("contact_lookup_unlocked", None),
        ("contact_lookup_for_update", None),
    ]


from __future__ import annotations

import pytest

from app.models.schema import Contact
from app.services.contact_intelligence_service import ContactIntelligenceService


@pytest.mark.asyncio
async def test_resolves_saved_whatsapp_contact_name_without_asking(db_session):
    contact = Contact(
        whatsapp_id="2348011111111@c.us",
        display_name="Mandy",
        contact_name="Amanda Christabel",
        push_name="Amanda C",
        normalized_phone="2348011111111",
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ContactIntelligenceService(db_session).resolve("Amanda Christabel")

    assert result["status"] == "resolved"
    assert result["match"]["contact_id"] == contact.id
    assert result["match"]["matched_field"] == "contact_name"
    assert result["confidence"] == pytest.approx(0.97)


@pytest.mark.asyncio
async def test_resolves_contact_alias_from_existing_identity_json(db_session):
    contact = Contact(
        whatsapp_id="2348022222222@c.us",
        display_name="Amanda Christabel",
        identity_json={"aliases": ["Mandy", "Amanda C"]},
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ContactIntelligenceService(db_session).resolve("Mandy")

    assert result["status"] == "resolved"
    assert result["match"]["contact_id"] == contact.id
    assert result["match"]["matched_field"] == "identity_json.aliases"


@pytest.mark.asyncio
async def test_phone_reference_resolves_against_existing_contact_identity(db_session):
    contact = Contact(
        whatsapp_id="2348033333333@c.us",
        display_name="Chris",
        normalized_phone="2348033333333",
    )
    db_session.add(contact)
    await db_session.flush()

    result = await ContactIntelligenceService(db_session).resolve("+234 803 333 3333")

    assert result["status"] == "resolved"
    assert result["match"]["contact_id"] == contact.id
    assert result["match"]["matched_field"] in {"whatsapp_id", "normalized_phone"}
    assert result["confidence"] >= 0.99


@pytest.mark.asyncio
async def test_ambiguous_short_name_returns_candidates_instead_of_guessing(db_session):
    first = Contact(whatsapp_id="2348044444444@c.us", contact_name="Amanda Christabel")
    second = Contact(whatsapp_id="2348055555555@c.us", contact_name="Amanda Chisom")
    db_session.add_all([first, second])
    await db_session.flush()

    result = await ContactIntelligenceService(db_session).resolve("Amanda")

    assert result["status"] == "ambiguous"
    assert result["match"] is None
    assert {item["contact_id"] for item in result["candidates"][:2]} == {first.id, second.id}
    assert result["margin"] < ContactIntelligenceService.AMBIGUITY_MARGIN

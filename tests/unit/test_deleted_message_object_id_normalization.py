from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import text

from app.models.schema import Contact, Message


AMANDA_ID = "2348000000199@c.us"


@pytest.mark.asyncio
async def test_object_valued_transport_ids_are_normalized_for_revocation(db_session):
    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()

    top_level = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="top object id",
        normalized_text="top object id",
        message_type="chat",
        raw_payload_json={
            "id": {"_serialized": "OBJECT-TOP-1", "fromMe": False},
            "chatId": AMANDA_ID,
        },
    )
    nested = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="nested object id",
        normalized_text="nested object id",
        message_type="chat",
        raw_payload_json={
            "message": {"id": {"id": "OBJECT-NESTED-1", "remote": AMANDA_ID}},
            "chatId": AMANDA_ID,
        },
    )
    fallback = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="nested fallback id",
        normalized_text="nested fallback id",
        message_type="chat",
        raw_payload_json={
            "id": {"unexpected": "not-a-transport-id"},
            "message": {"id": "OBJECT-NESTED-FALLBACK-1"},
            "chatId": AMANDA_ID,
        },
    )
    db_session.add_all([top_level, nested, fallback])
    await db_session.commit()

    rows = (
        await db_session.execute(
            text(
                "SELECT id, source_message_id FROM messages "
                "WHERE id IN (:top_id, :nested_id, :fallback_id) ORDER BY id"
            ),
            {
                "top_id": top_level.id,
                "nested_id": nested.id,
                "fallback_id": fallback.id,
            },
        )
    ).all()
    resolved = {row.id: row.source_message_id for row in rows}
    assert resolved[top_level.id] == "OBJECT-TOP-1"
    assert resolved[nested.id] == "OBJECT-NESTED-1"
    assert resolved[fallback.id] == "OBJECT-NESTED-FALLBACK-1"


@pytest.mark.asyncio
async def test_unusable_large_object_id_does_not_abort_message_persistence(db_session):
    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()

    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="large object id",
        normalized_text="large object id",
        message_type="chat",
        raw_payload_json={
            "id": {"unexpected": "x" * 500},
            "chatId": AMANDA_ID,
        },
    )
    db_session.add(message)
    await db_session.commit()

    source_message_id = (
        await db_session.execute(
            text("SELECT source_message_id FROM messages WHERE id=:id"),
            {"id": message.id},
        )
    ).scalar_one()
    assert source_message_id is None


def test_object_id_fix_is_additive_and_keeps_migration_027_unchanged() -> None:
    migration = Path("bot_core/migrations/028_deleted_message_object_id_normalization.sql").read_text(
        encoding="utf-8"
    )
    assert "zina_resolve_message_source_id" in migration
    assert "candidate->>'_serialized'" in migration
    assert "candidate->>'id'" in migration
    assert "LENGTH(resolved) <= 160" in migration
    assert "CREATE OR REPLACE FUNCTION zina_populate_message_source_id" in migration

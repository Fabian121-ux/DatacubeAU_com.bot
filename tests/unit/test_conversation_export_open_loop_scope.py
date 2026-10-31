from __future__ import annotations

import pytest

from app.models.conversation_open_loop import ConversationOpenLoop
from app.models.schema import Contact, Message
from app.services.conversation_export_service import ConversationExportService


@pytest.mark.asyncio
async def test_zina_chat_v1_open_loops_exclude_group_threads(db_session):
    contact = Contact(
        whatsapp_id="15550009991@c.us",
        display_name="Amanda",
        contact_name="Amanda",
    )
    db_session.add(contact)
    await db_session.flush()

    dm_message = Message(
        contact_id=contact.id,
        chat_id=contact.whatsapp_id,
        chat_type="dm",
        direction="inbound",
        message_text="Did you send the proposal?",
        normalized_text="did you send the proposal",
        message_type="text",
    )
    group_message = Message(
        contact_id=contact.id,
        chat_id="120363000000000000@g.us",
        chat_type="group",
        direction="inbound",
        message_text="Can you send the group file?",
        normalized_text="can you send the group file",
        message_type="text",
    )
    db_session.add_all([dm_message, group_message])
    await db_session.flush()

    dm_loop = ConversationOpenLoop(
        contact_id=contact.id,
        chat_id=contact.whatsapp_id,
        source_message_id=dm_message.id,
        last_message_id=dm_message.id,
        loop_type="question",
        loop_text=dm_message.message_text,
        normalized_text=dm_message.normalized_text,
        status="open",
    )
    group_loop = ConversationOpenLoop(
        contact_id=contact.id,
        chat_id=group_message.chat_id,
        source_message_id=group_message.id,
        last_message_id=group_message.id,
        loop_type="request",
        loop_text=group_message.message_text,
        normalized_text=group_message.normalized_text,
        status="open",
    )
    db_session.add_all([dm_loop, group_loop])
    await db_session.flush()

    rows = await ConversationExportService(db_session)._open_loops(contact.id)

    assert [row["text"] for row in rows] == ["Did you send the proposal?"]

    # Keep the shared fixture's generic cleanup order safe because open loops have
    # foreign keys to messages and are intentionally not part of older fixture cleanup.
    await db_session.delete(group_loop)
    await db_session.delete(dm_loop)
    await db_session.flush()

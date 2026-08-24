from __future__ import annotations

import pytest
from sqlalchemy import delete, select

from app.models.conversation_open_loop import ConversationOpenLoop
from app.models.schema import BotConfig, ConversationSummary, Message
from app.services.conversation_open_loop_service import (
    OPEN_LOOP_PROJECTION_SOURCE,
    SCAN_CURSOR_KEY,
    ConversationOpenLoopService,
)
from app.services.memory_service import MemoryService


async def _reset_open_loop_state(db_session) -> None:
    await db_session.execute(delete(ConversationOpenLoop))
    await db_session.execute(
        delete(ConversationSummary).where(ConversationSummary.source == OPEN_LOOP_PROJECTION_SOURCE)
    )
    await db_session.execute(delete(BotConfig).where(BotConfig.config_key == SCAN_CURSOR_KEY))
    await db_session.flush()


def _inbound(contact_id: int, chat_id: str, text: str) -> Message:
    return Message(
        contact_id=contact_id,
        chat_id=chat_id,
        chat_type="dm",
        direction="inbound",
        message_text=text,
        normalized_text=text.lower(),
    )


@pytest.mark.asyncio
async def test_open_question_becomes_durable_memory_context(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    message = _inbound(test_contact.id, test_contact.whatsapp_id, "Can Fabian send the proposal today?")
    db_session.add(message)
    await db_session.flush()

    result = await ConversationOpenLoopService(db_session).scan_once()
    await db_session.flush()

    assert result["created"] == 1
    loop = (await db_session.execute(select(ConversationOpenLoop))).scalar_one()
    assert loop.status == "open"
    assert loop.loop_type == "question"
    assert loop.source_message_id == message.id
    assert loop.last_message_id == message.id

    projection = (
        await db_session.execute(
            select(ConversationSummary).where(ConversationSummary.source == OPEN_LOOP_PROJECTION_SOURCE)
        )
    ).scalar_one()
    assert "Unresolved conversation items" in projection.summary
    assert "Can Fabian send the proposal today?" in projection.summary

    package = await MemoryService(db_session).get_context_package(test_contact.id)
    assert "Can Fabian send the proposal today?" in package.context_text
    assert any(row["source"] == OPEN_LOOP_PROJECTION_SOURCE for row in package.summaries)


@pytest.mark.asyncio
async def test_repeated_same_request_updates_one_open_loop(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    first = _inbound(test_contact.id, test_contact.whatsapp_id, "Please send me the address")
    db_session.add(first)
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    repeated = _inbound(test_contact.id, test_contact.whatsapp_id, "Please send me the address")
    db_session.add(repeated)
    await db_session.flush()
    result = await service.scan_once()

    loops = (await db_session.execute(select(ConversationOpenLoop))).scalars().all()
    assert result["repeated"] == 1
    assert len(loops) == 1
    assert loops[0].source_message_id == first.id
    assert loops[0].last_message_id == repeated.id
    assert loops[0].metadata_json["repeat_count"] == 2


@pytest.mark.asyncio
async def test_explicit_resolution_closes_single_loop_and_removes_projection(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    request = _inbound(test_contact.id, test_contact.whatsapp_id, "Could you remind Fabian about the meeting?")
    db_session.add(request)
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    resolved = _inbound(test_contact.id, test_contact.whatsapp_id, "That is sorted")
    db_session.add(resolved)
    await db_session.flush()
    result = await service.scan_once()

    loop = (await db_session.execute(select(ConversationOpenLoop))).scalar_one()
    assert result["resolved"] == 1
    assert loop.status == "resolved"
    assert loop.resolution_message_id == resolved.id
    assert loop.resolution_reason == "contact_explicit_resolution"
    projections = (
        await db_session.execute(
            select(ConversationSummary).where(ConversationSummary.source == OPEN_LOOP_PROJECTION_SOURCE)
        )
    ).scalars().all()
    assert projections == []


@pytest.mark.asyncio
async def test_ambiguous_resolution_does_not_close_multiple_loops(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    db_session.add_all(
        [
            _inbound(test_contact.id, test_contact.whatsapp_id, "Can Fabian review the proposal?"),
            _inbound(test_contact.id, test_contact.whatsapp_id, "Please send me the venue"),
        ]
    )
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    db_session.add(_inbound(test_contact.id, test_contact.whatsapp_id, "resolved"))
    await db_session.flush()
    result = await service.scan_once()

    assert result["resolved"] == 0
    active = await service.list_active(test_contact.id)
    assert len(active) == 2


@pytest.mark.asyncio
async def test_semantic_completion_resolves_matching_loop_with_multiple_open_items(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    db_session.add_all(
        [
            _inbound(test_contact.id, test_contact.whatsapp_id, "Can Fabian send the proposal?"),
            _inbound(test_contact.id, test_contact.whatsapp_id, "Please send me the venue address"),
        ]
    )
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    completion = _inbound(test_contact.id, test_contact.whatsapp_id, "I already received the proposal")
    db_session.add(completion)
    await db_session.flush()
    result = await service.scan_once()

    assert result["resolved"] == 1
    loops = (await db_session.execute(select(ConversationOpenLoop).order_by(ConversationOpenLoop.id))).scalars().all()
    proposal = next(row for row in loops if "proposal" in row.normalized_text)
    venue = next(row for row in loops if "venue" in row.normalized_text)
    assert proposal.status == "resolved"
    assert proposal.resolution_message_id == completion.id
    assert proposal.resolution_reason == "contact_semantic_resolution"
    assert proposal.metadata_json["resolution_score"] >= 0.60
    assert proposal.metadata_json["resolution_evidence"] == "I already received the proposal"
    assert venue.status == "open"

    projection = (
        await db_session.execute(
            select(ConversationSummary).where(ConversationSummary.source == OPEN_LOOP_PROJECTION_SOURCE)
        )
    ).scalar_one()
    assert "venue address" in projection.summary.lower()
    assert "proposal" not in projection.summary.lower()


@pytest.mark.asyncio
async def test_semantic_completion_stays_open_when_two_loops_match_equally(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    db_session.add_all(
        [
            _inbound(test_contact.id, test_contact.whatsapp_id, "Can Fabian send the proposal draft?"),
            _inbound(test_contact.id, test_contact.whatsapp_id, "Can Fabian review the proposal draft?"),
        ]
    )
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    db_session.add(_inbound(test_contact.id, test_contact.whatsapp_id, "I already received the proposal draft"))
    await db_session.flush()
    result = await service.scan_once()

    assert result["resolved"] == 0
    active = await service.list_active(test_contact.id)
    assert len(active) == 2


@pytest.mark.asyncio
async def test_completion_language_without_subject_overlap_does_not_resolve(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    db_session.add(_inbound(test_contact.id, test_contact.whatsapp_id, "Please send me the venue address"))
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)
    await service.scan_once()

    db_session.add(_inbound(test_contact.id, test_contact.whatsapp_id, "I already received the proposal"))
    await db_session.flush()
    result = await service.scan_once()

    assert result["resolved"] == 0
    active = await service.list_active(test_contact.id)
    assert len(active) == 1
    assert "venue" in active[0].normalized_text


@pytest.mark.asyncio
async def test_scan_cursor_prevents_reprocessing_non_loop_messages(db_session, test_contact) -> None:
    await _reset_open_loop_state(db_session)
    db_session.add(_inbound(test_contact.id, test_contact.whatsapp_id, "Good morning"))
    await db_session.flush()
    service = ConversationOpenLoopService(db_session)

    first = await service.scan_once()
    second = await service.scan_once()

    assert first["processed"] >= 1
    assert first["created"] == 0
    assert second == {"processed": 0, "created": 0, "repeated": 0, "resolved": 0}


def test_open_loop_classifier_is_conservative() -> None:
    classify = ConversationOpenLoopService.classify_open_loop
    assert classify("Can you send me the document?") == "question"
    assert classify("Please send me the document") == "request"
    assert classify("hello") is None
    assert classify("thanks") is None
    assert classify("that is sorted") is None


def test_semantic_resolution_scoring_is_grounded_and_conservative() -> None:
    score = ConversationOpenLoopService.semantic_resolution_score
    assert score("I already received the proposal", "Can Fabian send the proposal?") == 1.0
    assert score("I already received the proposal", "Please send me the venue address") == 0.0
    assert ConversationOpenLoopService.is_semantic_resolution_candidate("i already received the proposal") is True
    assert ConversationOpenLoopService.is_semantic_resolution_candidate("i was thinking about the proposal") is False

"""View-once observation wired into the real router.

The decisive invariant: observing a view-once message records metadata and nothing
else. It must never create an outbound row, never reach WAHA, and never change the
reply decision.
"""

from __future__ import annotations

import pytest
from sqlalchemy import select, text

from app.core.reply_planner import PlannedReply
from app.core.router import InboundRouter
from app.models.enums import DecisionType
from app.models.schema import Message, OutboundMessage


CONTACT_CHAT = "2348000000002@c.us"


async def _noop(*args, **kwargs):
    return None


def _event(*, message_id="SRC-1", view_once=False, media=True, chat_id=CONTACT_CHAT, body=""):
    payload = {
        "id": message_id,
        "chatId": chat_id,
        "from": chat_id,
        "fromMe": False,
        "body": body,
        "type": "image" if media else "chat",
    }
    if media:
        payload["hasMedia"] = True
        payload["media"] = {"url": "http://waha:3000/api/files/a.jpg", "mimetype": "image/jpeg"}
    if view_once:
        payload["isViewOnce"] = True
    return {"event": "message", "session": "test", "payload": payload}


async def _route(db_session, monkeypatch, event, *, should_reply=False):
    router = InboundRouter(db_session)

    async def _plan(*args, **kwargs):
        return PlannedReply(
            decision_type=DecisionType.IGNORE if not should_reply else DecisionType.STATIC_REPLY,
            reason="test",
            should_reply=should_reply,
            reply_text="ok" if should_reply else None,
        )

    monkeypatch.setattr(router.reply_planner, "plan", _plan)
    monkeypatch.setattr(router.reply_planner, "cache_answer_if_reusable", _noop)
    monkeypatch.setattr(router.reply_planner, "upsert_conversation_summary", _noop)
    monkeypatch.setattr(router, "_maybe_typing_delay", _noop)

    result = await router.process_event(event)
    await db_session.commit()
    return result


async def _metadata(db_session):
    rows = await db_session.execute(
        text("SELECT source_message_id, capability_state, transport_available FROM view_once_media_metadata")
    )
    return [dict(r) for r in rows.mappings().all()]


@pytest.mark.asyncio
async def test_view_once_message_is_observed_without_creating_any_outbound(db_session, monkeypatch):
    await _route(db_session, monkeypatch, _event(view_once=True))

    metadata = await _metadata(db_session)
    assert len(metadata) == 1
    assert metadata[0]["source_message_id"] == "SRC-1"

    outbound = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert outbound == []


@pytest.mark.asyncio
async def test_ordinary_media_message_records_no_view_once_metadata(db_session, monkeypatch):
    await _route(db_session, monkeypatch, _event(view_once=False))

    assert await _metadata(db_session) == []


@pytest.mark.asyncio
async def test_plain_text_message_records_no_metadata_and_still_persists(db_session, monkeypatch):
    await _route(db_session, monkeypatch, _event(media=False, body="hello", message_id="TXT-1"))

    assert await _metadata(db_session) == []
    messages = (await db_session.execute(select(Message))).scalars().all()
    assert len(messages) == 1


@pytest.mark.asyncio
async def test_observation_does_not_alter_the_reply_decision(db_session, monkeypatch):
    """A view-once message that warrants a reply still defers to the normal fence."""
    await _route(db_session, monkeypatch, _event(view_once=True, message_id="SRC-2"), should_reply=True)

    assert len(await _metadata(db_session)) == 1
    outbound = (await db_session.execute(select(OutboundMessage))).scalars().all()
    # An external contact reply is created but must remain deferred for approval.
    assert all(row.status == "deferred" for row in outbound)


@pytest.mark.asyncio
async def test_repeated_delivery_of_one_source_keeps_one_metadata_row(db_session, monkeypatch):
    event = _event(view_once=True, message_id="SRC-DUP")
    await _route(db_session, monkeypatch, event)
    await _route(db_session, monkeypatch, event)

    assert len(await _metadata(db_session)) == 1


@pytest.mark.asyncio
async def test_message_persistence_survives_observation_failure(db_session, monkeypatch):
    """Ingress must not lose a message because capability recording failed."""
    from app.services.view_once_observation_service import ViewOnceObservationService

    async def _boom(*args, **kwargs):
        raise RuntimeError("db down")

    monkeypatch.setattr(ViewOnceObservationService, "_upsert", _boom)

    await _route(db_session, monkeypatch, _event(view_once=True, message_id="SRC-FAIL"))

    messages = (await db_session.execute(select(Message))).scalars().all()
    assert len(messages) == 1
    assert await _metadata(db_session) == []

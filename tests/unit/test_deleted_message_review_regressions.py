from __future__ import annotations

from pathlib import Path

import pytest
from fastapi import BackgroundTasks
from sqlalchemy import select, text

from app.api import waha_events
from app.models.schema import AuditLog, Contact, Message
from app.workers import deleted_message_reconciliation_worker as reconciliation_worker


AMANDA_ID = "2348000000099@c.us"


@pytest.mark.asyncio
async def test_nested_transport_message_id_is_populated_and_revocable(db_session):
    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()
    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="nested id",
        normalized_text="nested id",
        message_type="chat",
        raw_payload_json={"message": {"id": "NESTED-REVOKE-1"}, "chatId": AMANDA_ID},
    )
    db_session.add(message)
    await db_session.commit()

    source_id = (
        await db_session.execute(
            text("SELECT source_message_id FROM messages WHERE id=:id"),
            {"id": message.id},
        )
    ).scalar_one()
    assert source_id == "NESTED-REVOKE-1"


@pytest.mark.asyncio
async def test_durable_worker_reconciles_committed_message_after_unmatched_revoke(db_session, monkeypatch):
    contact = Contact(whatsapp_id=AMANDA_ID, chat_id=AMANDA_ID, display_name="Amanda")
    db_session.add(contact)
    await db_session.flush()
    db_session.add(
        AuditLog(
            action="message_revocation_unmatched",
            entity_type="message",
            entity_id="LATE-DURABLE-1",
            details_json={
                "revoked_message_id": "LATE-DURABLE-1",
                "chat_id": AMANDA_ID,
                "content_recovered": False,
            },
        )
    )
    await db_session.commit()

    message = Message(
        contact_id=contact.id,
        chat_id=AMANDA_ID,
        chat_type="dm",
        direction="inbound",
        message_text="arrived later",
        normalized_text="arrived later",
        message_type="chat",
        raw_payload_json={"message": {"id": "LATE-DURABLE-1"}, "chatId": AMANDA_ID},
    )
    db_session.add(message)
    await db_session.commit()

    class _ReusableSessionContext:
        async def __aenter__(self):
            return db_session

        async def __aexit__(self, exc_type, exc, tb):
            return False

    monkeypatch.setattr(reconciliation_worker, "SessionLocal", lambda: _ReusableSessionContext())
    assert await reconciliation_worker._reconcile_pending_batch(limit=10) == 1

    lifecycle = (
        await db_session.execute(
            text("SELECT lifecycle_status FROM messages WHERE id=:id"),
            {"id": message.id},
        )
    ).scalar_one()
    assert lifecycle == "revoked"


@pytest.mark.asyncio
async def test_eventless_accepted_message_schedules_opportunistic_reconciliation(monkeypatch):
    captured: list[tuple[str, str | None]] = []

    async def _accepted(_request, _background_tasks):
        return {"status": "accepted"}

    async def _capture(source_message_id: str, chat_id: str | None):
        captured.append((source_message_id, chat_id))

    monkeypatch.setattr(waha_events.inbound, "waha_webhook", _accepted)
    monkeypatch.setattr(waha_events, "_reconcile_after_message", _capture)

    class _Request:
        async def json(self):
            return {"id": "EVENTLESS-1", "chatId": AMANDA_ID, "body": "hello"}

    tasks = BackgroundTasks()
    response = await waha_events.waha_events_webhook(_Request(), tasks)
    assert response["status"] == "accepted"
    await tasks()
    assert captured == [("EVENTLESS-1", AMANDA_ID)]


def test_production_docs_and_deploy_script_require_revocation_gateway() -> None:
    readme = Path("README.md").read_text(encoding="utf-8")
    deploy_script = Path("deploy/scripts/deploy.sh").read_text(encoding="utf-8")

    assert "WHATSAPP_HOOK_URL=http://api:8080/webhooks/waha-events" in readme
    assert "WHATSAPP_HOOK_EVENTS=message,message.any,message.revoked" in readme
    assert 'EXPECTED_HOOK_URL="http://api:8080/webhooks/waha-events"' in deploy_script
    assert "WHATSAPP_HOOK_EVENTS must include message.revoked" in deploy_script


def test_migration_backfills_and_indexes_nested_transport_ids() -> None:
    migration = Path("bot_core/migrations/026_deleted_message_lifecycle.sql").read_text(encoding="utf-8")
    assert "raw_payload_json->'message'->>'id'" in migration
    assert "zina_populate_message_source_id" in migration
    assert "idx_messages_raw_nested_message_id" in migration

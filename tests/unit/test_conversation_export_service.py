from __future__ import annotations

from datetime import datetime, timezone

import pytest

from app.models.schema import Contact
from app.services.conversation_export_service import ConversationExportService


class _FakeTools:
    async def execute(self, name, arguments, *, context):
        assert name == "chat.read"
        assert arguments == {
            "contact": "Amanda Christabel",
            "limit": 25,
            "after": "2026-08-01T00:00:00+00:00",
        }
        assert context.permission == "owner"
        assert context.requested_by_contact_id == 91
        return {
            "handler_target": "tool_dispatcher:chat.read",
            "result": {
                "contact_id": 77,
                "contact_resolution": {
                    "status": "resolved",
                    "confidence": 0.98,
                    "matched_field": "contact_name",
                },
                "message_count": 2,
                "limit": 25,
                "after": datetime(2026, 8, 1, tzinfo=timezone.utc),
                "before": None,
                "window": {
                    "oldest_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
                    "newest_at": datetime(2026, 8, 20, 8, 5, tzinfo=timezone.utc),
                },
                "messages": [
                    {
                        "id": 11,
                        "direction": "inbound",
                        "text": "Did you send the proposal?",
                        "message_type": "text",
                        "created_at": datetime(2026, 8, 20, 8, 0, tzinfo=timezone.utc),
                    },
                    {
                        "id": "delivery:92",
                        "direction": "outbound",
                        "text": "I will send it today.",
                        "message_type": "text",
                        "created_at": datetime(2026, 8, 20, 8, 5, tzinfo=timezone.utc),
                    },
                ],
            },
        }


class _FakeSession:
    def __init__(self, contact):
        self.contact = contact

    async def get(self, model, identity):
        assert model is Contact
        assert identity == 77
        return self.contact


class _ExportUnderTest(ConversationExportService):
    async def _relationship(self, contact_id):
        assert contact_id == 77
        return {"type": "friend", "relationship": "close friend"}

    async def _memory_facts(self, contact_id):
        assert contact_id == 77
        return [{"id": 1, "text": "Amanda is waiting for the proposal."}]

    async def _summaries(self, contact_id):
        assert contact_id == 77
        return [{"id": 2, "summary": "Discussed the proposal.", "source": "threshold_summary"}]

    async def _open_loops(self, contact_id):
        assert contact_id == 77
        return [{"id": 3, "type": "question", "text": "Did you send the proposal?"}]

    async def _scheduled_actions(self, contact_id):
        assert contact_id == 77
        return [{"id": 4, "action_type": "whatsapp.send_message", "status": "scheduled"}]


@pytest.mark.asyncio
async def test_zina_chat_v1_composes_existing_authoritative_sources():
    contact = Contact(
        id=77,
        whatsapp_id="2348011111111@c.us",
        display_name="Amanda Christabel",
        contact_name="Amanda Christabel",
        push_name="Mandy",
        normalized_phone="2348011111111",
        identity_source="waha_contact_sync",
        identity_json={"aliases": ["Amanda", "Mandy"]},
        is_name_verified=True,
    )
    service = _ExportUnderTest(_FakeSession(contact))
    service.tools = _FakeTools()

    payload = await service.export(
        contact_reference="Amanda Christabel",
        limit=25,
        after=datetime(2026, 8, 1, tzinfo=timezone.utc),
        requested_by_contact_id=91,
    )

    assert payload["schema_version"] == "zina.chat.v1"
    assert payload["contact"]["contact_id"] == 77
    assert payload["contact"]["aliases"] == ["Amanda", "Mandy"]
    assert payload["relationship"]["type"] == "friend"
    assert payload["conversation"]["message_count"] == 2
    assert payload["conversation"]["messages"][1]["text"] == "I will send it today."
    assert payload["memory"]["facts"][0]["text"] == "Amanda is waiting for the proposal."
    assert payload["open_loops"][0]["text"] == "Did you send the proposal?"
    assert payload["zina_activity"]["scheduled_actions"][0]["status"] == "scheduled"
    assert payload["analysis"]["status"] == "not_generated"
    assert payload["provenance"]["chat_history_tool"] == "chat.read"
    assert payload["provenance"]["contact_resolution"]["matched_field"] == "contact_name"


def test_contact_projection_exposes_aliases_without_raw_identity_json():
    contact = Contact(
        id=8,
        whatsapp_id="15550000008@c.us",
        identity_json={"aliases": ["Ada"], "private_transport_blob": {"ignored": True}},
    )

    payload = ConversationExportService._contact_payload(contact)

    assert payload["aliases"] == ["Ada"]
    assert "identity_json" not in payload
    assert "private_transport_blob" not in payload

from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import natural_actions_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeDb:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


class _FakePlanner:
    def __init__(self, _db):
        pass

    async def create_from_instruction(self, instruction, **kwargs):
        if "unsupported" in instruction:
            return None
        return {
            "action": "whatsapp.send_message",
            "plan": {
                "target_reference": "Amanda Christabel",
                "scheduled_for": "2026-08-25T09:00:00+01:00",
                "timezone": kwargs["timezone"],
                "date_phrase": "Aug 25",
                "time_phrase": "9am",
            },
            "scheduled_action": {
                "id": 51,
                "status": "scheduled",
                "target_chat_id": "2348011111111@c.us",
            },
        }


class _AmbiguousPlanner(_FakePlanner):
    async def create_from_instruction(self, instruction, **kwargs):
        error = ValueError("target contact is ambiguous")
        error.resolution = {"status": "ambiguous", "candidates": [{"contact_id": 1}, {"contact_id": 2}]}
        raise error


async def _fake_db():
    yield _FakeDb()


def _client():
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


def test_admin_can_create_structured_action_from_natural_instruction(monkeypatch):
    monkeypatch.setattr(natural_actions_admin, "NaturalActionPlannerService", _FakePlanner)
    client = _client()
    try:
        response = client.post(
            "/admin/natural-actions/whatsapp-message",
            json={
                "instruction": "message Amanda Christabel at 9am on Aug 25 and tell her the document is ready",
                "timezone": "Africa/Lagos",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["action"] == "whatsapp.send_message"
        assert body["scheduled_action"]["id"] == 51
        assert body["plan"]["target_reference"] == "Amanda Christabel"
    finally:
        app.dependency_overrides.clear()


def test_admin_natural_action_surface_rejects_unsupported_grammar(monkeypatch):
    monkeypatch.setattr(natural_actions_admin, "NaturalActionPlannerService", _FakePlanner)
    client = _client()
    try:
        response = client.post(
            "/admin/natural-actions/whatsapp-message",
            json={"instruction": "unsupported request", "timezone": "Africa/Lagos"},
        )
        assert response.status_code == 422
        assert "unsupported natural action" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_admin_natural_action_preserves_contact_ambiguity_evidence(monkeypatch):
    monkeypatch.setattr(natural_actions_admin, "NaturalActionPlannerService", _AmbiguousPlanner)
    client = _client()
    try:
        response = client.post(
            "/admin/natural-actions/whatsapp-message",
            json={"instruction": "message Amanda at 9am tomorrow and tell her hello", "timezone": "Africa/Lagos"},
        )
        assert response.status_code == 409
        assert response.json()["detail"]["resolution"]["status"] == "ambiguous"
    finally:
        app.dependency_overrides.clear()

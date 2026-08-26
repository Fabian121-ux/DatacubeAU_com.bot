from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import scheduled_actions_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeDb:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


class _FakeService:
    def __init__(self, _db):
        pass

    async def create_whatsapp_message(self, **kwargs):
        return {"id": 41, "status": "scheduled", "target_chat_id": "2348011111111@c.us"}

    async def list(self, *, status=None, limit=100):
        return [{"id": 41, "status": status or "scheduled"}]

    async def cancel(self, action_id):
        return {"id": action_id, "status": "cancelled"}

    async def pause(self, action_id):
        return {"id": action_id, "status": "paused"}

    async def resume(self, action_id):
        return {"id": action_id, "status": "scheduled"}

    async def run_now(self, action_id):
        return {"id": action_id, "status": "scheduled"}

    async def reschedule(self, action_id, *, scheduled_for, timezone=None):
        return {"id": action_id, "status": "scheduled", "timezone": timezone}


class _RejectNaiveTimeService(_FakeService):
    async def create_whatsapp_message(self, **kwargs):
        scheduled_for = kwargs["scheduled_for"]
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            raise ValueError("scheduled_for must include a timezone offset")
        return await super().create_whatsapp_message(**kwargs)


async def _fake_db():
    yield _FakeDb()


def _client():
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


def test_admin_can_create_and_list_scheduled_whatsapp_action(monkeypatch):
    monkeypatch.setattr(scheduled_actions_admin, "ScheduledActionService", _FakeService)
    client = _client()
    try:
        response = client.post(
            "/admin/scheduled-actions",
            json={
                "target": "Amanda Christabel",
                "text": "Good morning Amanda.",
                "scheduled_for": "2026-08-25T09:00:00+01:00",
                "timezone": "Africa/Lagos",
            },
        )
        assert response.status_code == 200
        assert response.json()["item"]["id"] == 41

        listed = client.get("/admin/scheduled-actions", params={"status": "scheduled"})
        assert listed.status_code == 200
        assert listed.json()["count"] == 1
    finally:
        app.dependency_overrides.clear()


def test_admin_scheduler_controls_are_exposed(monkeypatch):
    monkeypatch.setattr(scheduled_actions_admin, "ScheduledActionService", _FakeService)
    client = _client()
    try:
        assert client.post("/admin/scheduled-actions/41/pause").json()["item"]["status"] == "paused"
        assert client.post("/admin/scheduled-actions/41/resume").json()["item"]["status"] == "scheduled"
        assert client.post("/admin/scheduled-actions/41/run-now").status_code == 200
        rescheduled = client.post(
            "/admin/scheduled-actions/41/reschedule",
            json={"scheduled_for": "2026-08-25T11:00:00+01:00", "timezone": "Africa/Lagos"},
        )
        assert rescheduled.status_code == 200
        assert client.post("/admin/scheduled-actions/41/cancel").json()["item"]["status"] == "cancelled"
    finally:
        app.dependency_overrides.clear()


def test_scheduler_rejects_naive_timestamp_with_clear_error(monkeypatch):
    monkeypatch.setattr(scheduled_actions_admin, "ScheduledActionService", _RejectNaiveTimeService)
    client = _client()
    try:
        response = client.post(
            "/admin/scheduled-actions",
            json={
                "target": "Amanda",
                "text": "Hello",
                "scheduled_for": "2026-08-25T09:00:00",
                "timezone": "Africa/Lagos",
            },
        )
        assert response.status_code == 409
        assert response.json()["detail"] == "scheduled_for must include a timezone offset"
    finally:
        app.dependency_overrides.clear()

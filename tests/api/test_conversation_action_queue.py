from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import conversation_takeover_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeHandbackService:
    def __init__(self, _db):
        pass

    async def get_latest(self, *, chat_id: str):
        assert chat_id == "15550001101@c.us"
        return {
            "generated_at": "2026-08-23T20:00:00+00:00",
            "fabian_action_queue": [
                {
                    "recommended_action": "reply_now",
                    "source_id": 101,
                    "evidence": "Can Fabian confirm today?",
                },
                {
                    "recommended_action": "review_today",
                    "source_id": 102,
                    "evidence": "A Zina reply was cancelled when Fabian returned.",
                },
                {
                    "recommended_action": "informational",
                    "source_id": 103,
                    "evidence": "Thanks.",
                },
            ],
        }


async def _fake_db():
    yield object()


def _client(monkeypatch) -> TestClient:
    monkeypatch.setattr(conversation_takeover_admin, "ConversationHandbackService", _FakeHandbackService)
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


def test_action_queue_returns_latest_private_queue(monkeypatch):
    client = _client(monkeypatch)
    try:
        response = client.get("/admin/conversation-takeovers/15550001101@c.us/action-queue")
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 3
        assert body["action_filter"] is None
        assert body["generated_at"] == "2026-08-23T20:00:00+00:00"
        assert body["items"][0]["recommended_action"] == "reply_now"
    finally:
        app.dependency_overrides.clear()


def test_action_queue_filters_without_recomputing_evidence(monkeypatch):
    client = _client(monkeypatch)
    try:
        response = client.get(
            "/admin/conversation-takeovers/15550001101@c.us/action-queue",
            params={"action": "review_today"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["action_filter"] == "review_today"
        assert body["items"][0]["source_id"] == 102
    finally:
        app.dependency_overrides.clear()


def test_action_queue_rejects_unknown_filter(monkeypatch):
    client = _client(monkeypatch)
    try:
        response = client.get(
            "/admin/conversation-takeovers/15550001101@c.us/action-queue",
            params={"action": "invented_deadline"},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

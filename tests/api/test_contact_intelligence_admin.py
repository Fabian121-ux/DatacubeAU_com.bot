from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import contact_intelligence_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeResolver:
    def __init__(self, _db):
        pass

    async def resolve(self, query: str, *, limit: int = 5):
        assert query == "Amanda Christabel"
        assert limit == 3
        return {
            "query": query,
            "status": "resolved",
            "confidence": 0.97,
            "margin": 0.97,
            "match": {
                "contact_id": 77,
                "whatsapp_id": "2348011111111@c.us",
                "contact_name": "Amanda Christabel",
                "matched_field": "contact_name",
            },
            "candidates": [
                {
                    "contact_id": 77,
                    "whatsapp_id": "2348011111111@c.us",
                    "contact_name": "Amanda Christabel",
                    "confidence": 0.97,
                    "matched_field": "contact_name",
                }
            ],
        }


class _FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, item):
        self.added.append(item)

    async def commit(self):
        self.committed = True


async def _fake_db():
    yield _FakeDb()


def test_contact_resolution_admin_endpoint_uses_explainable_resolver(monkeypatch):
    monkeypatch.setattr(contact_intelligence_admin, "ContactIntelligenceService", _FakeResolver)
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    client = TestClient(app)
    try:
        response = client.get(
            "/admin/contact-intelligence/resolve",
            params={"q": "Amanda Christabel", "limit": 3},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "resolved"
        assert body["match"]["contact_id"] == 77
        assert body["match"]["matched_field"] == "contact_name"
    finally:
        app.dependency_overrides.clear()


def test_contact_resolution_admin_endpoint_rejects_empty_query(monkeypatch):
    monkeypatch.setattr(contact_intelligence_admin, "ContactIntelligenceService", _FakeResolver)
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    client = TestClient(app)
    try:
        response = client.get("/admin/contact-intelligence/resolve", params={"q": ""})
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

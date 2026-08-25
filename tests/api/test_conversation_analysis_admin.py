from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import conversation_analysis_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeAnalysisService:
    def __init__(self, _db):
        pass

    async def analyze(self, *, contact_reference, limit, after, before, requested_by_contact_id=None):
        assert contact_reference == "Amanda Christabel"
        assert limit == 50
        assert after.isoformat() == "2026-08-01T00:00:00+00:00"
        assert before is None
        assert requested_by_contact_id is None
        return {
            "schema_version": "zina.chat.analysis.v1",
            "conversation_schema_version": "zina.chat.v1",
            "contact": {"contact_id": 77, "display_name": "Amanda Christabel"},
            "message_count": 3,
            "analysis": {
                "status": "generated",
                "method": "deterministic_evidence_projection",
                "unresolved_matters": [],
                "explicit_commitments": [],
                "recurring_topics": [],
                "important_dates": [],
                "recommended_follow_ups": [],
            },
            "provenance": {"llm_used": False},
        }


class _FakeDb:
    def __init__(self):
        self.committed = False

    async def commit(self):
        self.committed = True


async def _fake_db():
    yield _FakeDb()


def _client_with_admin_override():
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


def test_conversation_analysis_endpoint_returns_evidence_projection(monkeypatch):
    monkeypatch.setattr(conversation_analysis_admin, "ConversationAnalysisService", _FakeAnalysisService)
    client = _client_with_admin_override()
    try:
        response = client.get(
            "/admin/conversation-analysis",
            params={
                "contact": "Amanda Christabel",
                "limit": 50,
                "after": "2026-08-01T00:00:00Z",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["schema_version"] == "zina.chat.analysis.v1"
        assert body["analysis"]["status"] == "generated"
        assert body["provenance"]["llm_used"] is False
    finally:
        app.dependency_overrides.clear()


def test_conversation_analysis_endpoint_keeps_admin_authentication():
    client = TestClient(app)
    response = client.get("/admin/conversation-analysis", params={"contact": "Amanda"}, follow_redirects=False)
    assert response.status_code in {302, 303, 307, 401}


def test_conversation_analysis_endpoint_rejects_unbounded_limit(monkeypatch):
    monkeypatch.setattr(conversation_analysis_admin, "ConversationAnalysisService", _FakeAnalysisService)
    client = _client_with_admin_override()
    try:
        response = client.get(
            "/admin/conversation-analysis",
            params={"contact": "Amanda", "limit": 201},
        )
        assert response.status_code == 422
    finally:
        app.dependency_overrides.clear()

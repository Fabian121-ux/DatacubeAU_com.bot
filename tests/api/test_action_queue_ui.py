from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import require_admin_session
from app.main import app


def test_action_queue_ui_requires_admin_session():
    app.dependency_overrides.clear()
    with TestClient(app, follow_redirects=False) as client:
        response = client.get("/admin/action-queue")
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_action_queue_ui_renders_private_evidence_view():
    app.dependency_overrides[require_admin_session] = lambda: object()
    try:
        with TestClient(app) as client:
            response = client.get("/admin/action-queue")
        assert response.status_code == 200
        assert "Fabian Action Queue" in response.text
        assert "reply_now" in response.text
        assert "review_today" in response.text
        assert "informational" in response.text
        assert "/admin/conversation-takeovers/" in response.text
        assert "source_id" in response.text
        assert "reason_codes" in response.text
        assert "credentials:'same-origin'" in response.text
    finally:
        app.dependency_overrides.clear()

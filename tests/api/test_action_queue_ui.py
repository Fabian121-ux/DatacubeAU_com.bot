from __future__ import annotations

from fastapi.testclient import TestClient

from app.api.deps import require_admin_session
from app.main import app


def test_action_queue_ui_requires_admin_session():
    app.dependency_overrides.clear()
    client = TestClient(app, follow_redirects=False)
    response = client.get("/admin/action-queue")
    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_action_queue_ui_renders_private_evidence_view():
    app.dependency_overrides[require_admin_session] = lambda: object()
    try:
        client = TestClient(app)
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


def test_action_queue_ui_supports_shareable_chat_and_filter_deep_links():
    app.dependency_overrides[require_admin_session] = lambda: object()
    try:
        client = TestClient(app)
        response = client.get("/admin/action-queue?chat_id=15550001101%40c.us&action=review_today")
        assert response.status_code == 200
        assert "new URLSearchParams(window.location.search)" in response.text
        assert "pageParams.get('chat_id')" in response.text
        assert "pageParams.get('action')" in response.text
        assert "if(initialChatId)loadQueue();" in response.text
        assert "history.replaceState" in response.text
        assert 'href="/admin/ui#inspector"' in response.text
    finally:
        app.dependency_overrides.clear()

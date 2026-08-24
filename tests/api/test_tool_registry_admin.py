from __future__ import annotations

from fastapi.testclient import TestClient

from app.api import tool_registry_admin
from app.api.deps import require_admin_session
from app.db import get_db_session
from app.main import app


class _FakeDb:
    def __init__(self):
        self.added = []
        self.committed = False

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.committed = True


class _FakeRegistry:
    enabled = True

    def __init__(self, _db):
        pass

    async def list_tools(self):
        return [
            {
                "name": "whatsapp.send_message",
                "category": "WhatsApp",
                "description": "Send message",
                "risk": "medium",
                "permission": "owner",
                "input_schema": {"type": "object"},
                "handler_target": "scheduled_action.whatsapp_send_message",
                "enabled": self.enabled,
            }
        ]

    async def get_tool(self, name):
        if name != "whatsapp.send_message":
            return None
        return (await self.list_tools())[0]

    async def set_enabled(self, name, enabled):
        if name != "whatsapp.send_message":
            raise ValueError(f"tool {name} not found")
        type(self).enabled = enabled
        return (await self.list_tools())[0]


async def _fake_db():
    yield _FakeDb()


def _client():
    app.dependency_overrides[require_admin_session] = lambda: object()
    app.dependency_overrides[get_db_session] = _fake_db
    return TestClient(app)


def test_admin_lists_tool_contracts(monkeypatch):
    monkeypatch.setattr(tool_registry_admin, "ToolRegistryService", _FakeRegistry)
    client = _client()
    try:
        response = client.get("/admin/tools")
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1
        assert body["items"][0]["name"] == "whatsapp.send_message"
        assert body["items"][0]["risk"] == "medium"
    finally:
        app.dependency_overrides.clear()


def test_admin_can_toggle_known_tool(monkeypatch):
    monkeypatch.setattr(tool_registry_admin, "ToolRegistryService", _FakeRegistry)
    _FakeRegistry.enabled = True
    client = _client()
    try:
        response = client.post("/admin/tools/whatsapp.send_message/toggle", json={"enabled": False})
        assert response.status_code == 200
        assert response.json()["item"]["enabled"] is False
    finally:
        app.dependency_overrides.clear()


def test_admin_cannot_enable_unregistered_au_beta_tool(monkeypatch):
    monkeypatch.setattr(tool_registry_admin, "ToolRegistryService", _FakeRegistry)
    client = _client()
    try:
        response = client.post("/admin/tools/au.reason/toggle", json={"enabled": True})
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()

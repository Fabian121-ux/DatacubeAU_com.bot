from __future__ import annotations

import pytest

from app.services.tool_registry_service import ToolRegistryService


@pytest.mark.asyncio
async def test_planner_catalog_exposes_only_intentionally_executable_tools(db_session):
    service = ToolRegistryService(db_session)

    items = await service.planner_catalog(permission="owner")
    by_name = {item["name"]: item for item in items}

    assert "whatsapp.find_contact" in by_name
    assert "whatsapp.send_message" in by_name
    assert "memory.search" in by_name
    assert "chat.read" in by_name
    assert "task.create" not in by_name
    assert "task.cancel" not in by_name
    assert "web.search" not in by_name
    assert "group.tag" not in by_name
    assert "au.reason" not in by_name
    assert all("handler_target" not in item for item in items)
    assert all("permission" not in item for item in items)


@pytest.mark.asyncio
async def test_planner_catalog_respects_permission_and_disabled_state(db_session):
    service = ToolRegistryService(db_session)

    assert await service.planner_catalog(permission="admin") == []
    assert await service.planner_catalog(permission="user") == []

    await service.set_enabled("chat.read", False)
    items = await service.planner_catalog(permission="owner")
    assert "chat.read" not in {item["name"] for item in items}

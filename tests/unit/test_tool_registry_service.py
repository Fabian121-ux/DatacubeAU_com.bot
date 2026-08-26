from __future__ import annotations

import pytest

from app.services.tool_registry_service import ToolRegistryService


class _FakeConfig:
    def __init__(self):
        self.values: dict[str, str] = {}

    async def get_bool(self, key: str, default: bool = False) -> bool:
        if key not in self.values:
            return default
        return self.values[key] == "true"

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


@pytest.fixture
def registry():
    service = ToolRegistryService(object())
    service.config = _FakeConfig()
    return service


@pytest.mark.asyncio
async def test_registry_exposes_risk_permission_schema_and_handler(registry):
    tool = await registry.get_tool("whatsapp.send_message")

    assert tool is not None
    assert tool["risk"] == "medium"
    assert tool["permission"] == "owner"
    assert tool["handler_target"] == "scheduled_action.whatsapp_send_message"
    assert set(tool["input_schema"]["required"]) == {"target", "text"}
    assert tool["enabled"] is True


@pytest.mark.asyncio
async def test_registry_persists_enable_disable_state_without_new_tool_store(registry):
    disabled = await registry.set_enabled("whatsapp.send_message", False)
    assert disabled["enabled"] is False
    assert registry.config.values["tool.whatsapp.send_message.enabled"] == "false"

    enabled = await registry.set_enabled("WHATSAPP.SEND_MESSAGE", True)
    assert enabled["enabled"] is True


@pytest.mark.asyncio
async def test_future_group_mutation_is_disabled_by_default(registry):
    tool = await registry.get_tool("group.tag")
    assert tool is not None
    assert tool["risk"] == "medium"
    assert tool["enabled"] is False


@pytest.mark.asyncio
async def test_unknown_tools_are_not_executable_or_toggleable(registry):
    assert await registry.get_tool("au.reason") is None
    assert await registry.is_enabled("au.reason") is False
    with pytest.raises(ValueError, match="not found"):
        await registry.set_enabled("au.reason", True)

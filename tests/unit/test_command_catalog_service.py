from __future__ import annotations

from app.services.command_catalog_service import DEFAULT_COMMANDS, CommandCatalogService
from app.services.internet_service import INTERNET_COMMANDS
from app.services.owner_command_service import OwnerCommandService


def test_command_catalog_covers_current_command_surface() -> None:
    names = {item.name for item in DEFAULT_COMMANDS}

    assert not (OwnerCommandService.OWNER_COMMANDS - names)
    assert not (OwnerCommandService.USER_COMMANDS - names)
    assert not (set(INTERNET_COMMANDS) - names)
    assert len(names) == len(DEFAULT_COMMANDS)


def test_command_catalog_has_required_sections_and_metadata() -> None:
    required_sections = {
        "User Commands",
        "Admin Commands",
        "Internet Commands",
        "Media Commands",
        "Memory Commands",
    }
    categories = {item.category for item in DEFAULT_COMMANDS}

    assert required_sections <= categories
    for item in DEFAULT_COMMANDS:
        assert item.description
        assert item.example
        assert item.permissions in {"user", "owner"}
        serialized = CommandCatalogService.serialize_default(item)
        assert serialized["trigger_syntax"]
        assert serialized["handler_target"]
        assert serialized["usage_count"] == 0


def test_command_catalog_assigns_handler_targets() -> None:
    by_name = {item.name: item for item in DEFAULT_COMMANDS}

    assert by_name["/help"].name in OwnerCommandService.USER_COMMANDS
    assert by_name["/status"].name in OwnerCommandService.USER_COMMANDS
    assert by_name["/start"].name in OwnerCommandService.USER_COMMANDS
    assert CommandCatalogService.default_handler_target("/help") == "user_command:/help"
    assert CommandCatalogService.default_handler_target("/global") == "memory:global_chat"
    assert CommandCatalogService.default_handler_target("!ask") == "ai:one_shot"
    assert CommandCatalogService.default_handler_target("!search") == "internet_command:!search"

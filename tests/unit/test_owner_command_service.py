from __future__ import annotations

from types import SimpleNamespace

import pytest

from app.core.message_normalizer import MessageNormalizer
from app.services.owner_command_service import OwnerCommandService


def test_extract_command_and_args() -> None:
    command, args = OwnerCommandService.extract_command("/remember Datacube AU is active")

    assert command == "/remember"
    assert args == "Datacube AU is active"


def test_extract_command_ignores_non_commands() -> None:
    command, args = OwnerCommandService.extract_command("hello")

    assert command is None
    assert args == ""


def test_owner_id_matching_accepts_full_id_or_digits() -> None:
    configured = "2348012345678@c.us,15550000001"

    assert OwnerCommandService.is_owner_id_static("2348012345678@c.us", configured)
    assert OwnerCommandService.is_owner_id_static("15550000001@c.us", configured)
    assert OwnerCommandService.is_owner_id_static("+1 (555) 000-0001", configured)
    assert OwnerCommandService.is_owner_id_static("15550000001@s.whatsapp.net", configured)
    assert OwnerCommandService.is_owner_id_static("15550000001@lid", configured)
    assert not OwnerCommandService.is_owner_id_static("15550000002@c.us", configured)


def test_owner_identity_keys_include_waha_alternate_ids() -> None:
    message = SimpleNamespace(
        sender_id="1234567890@lid",
        sender_alternate_ids=["15550000001@c.us"],
        payload={"sender": {"phone": "+1 555 000 0001"}},
    )

    keys = OwnerCommandService.identity_keys_for_message(message)

    assert "1234567890@lid" in keys
    assert "15550000001@c.us" in keys
    assert "15550000001@s.whatsapp.net" in keys


def test_message_normalizer_preserves_lid_and_phone_sender_alternates() -> None:
    normalized = MessageNormalizer().normalize(
        {
            "chatId": "15550000001@c.us",
            "from": "1234567890@lid",
            "sender": {"phone": "+1 555 000 0001", "pushName": "Fabian"},
            "text": {"body": "/whoami"},
            "isGroup": False,
        }
    )

    assert normalized.sender_id == "1234567890@lid"
    assert "15550000001@c.us" in normalized.sender_alternate_ids
    assert "+1 555 000 0001" in normalized.sender_alternate_ids
    assert normalized.sender_name == "Fabian"


def test_message_normalizer_uses_contact_name_when_push_name_missing() -> None:
    normalized = MessageNormalizer().normalize(
        {
            "chatId": "15550000001@c.us",
            "from": "15550000001@c.us",
            "contact": {"name": "Fabian Contact"},
            "text": {"body": "kk"},
        }
    )

    assert normalized.sender_name == "Fabian Contact"


@pytest.mark.asyncio
async def test_whoami_reports_owner_status_from_waha_alternate_id() -> None:
    class Config:
        async def get(self, *_args):
            return "15550000001"

    service = OwnerCommandService.__new__(OwnerCommandService)
    service.config = Config()
    message = SimpleNamespace(
        sender_id="1234567890@lid",
        sender_alternate_ids=["15550000001@c.us"],
        payload={"sender": {"phone": "+1 555 000 0001"}},
    )

    reply = await service._whoami(message)

    assert "Owner: Yes" in reply
    assert "Detected:\n1234567890@lid" in reply
    assert "Normalized:\n1234567890@c.us" in reply
    assert "Permissions:\nFull" in reply
    assert "15550000001@c.us" in reply


def test_parse_label_blocks_for_teach_command() -> None:
    blocks = OwnerCommandService.parse_label_blocks(
        "Question:\nWhat is Zina?\n\nAnswer:\nZina is Fabian's AI assistant."
    )

    assert blocks["question"] == "What is Zina?"
    assert blocks["answer"] == "Zina is Fabian's AI assistant."


def test_parse_label_blocks_for_custom_command() -> None:
    blocks = OwnerCommandService.parse_label_blocks(
        "Command:\n/scholarship\nReply:\nCheck School Info updates."
    )

    assert blocks["command"] == "/scholarship"
    assert blocks["reply"] == "Check School Info updates."


def test_clean_target_accepts_markdown_mailto_ids() -> None:
    assert (
        OwnerCommandService.clean_target("[120363222222222222@g.us](mailto:120363222222222222@g.us)")
        == "120363222222222222@g.us"
    )


def test_group_metadata_commands_are_owner_commands() -> None:
    assert "/group-sync" in OwnerCommandService.OWNER_COMMANDS
    assert "/tag-group" in OwnerCommandService.OWNER_COMMANDS
    assert "/group-notes" in OwnerCommandService.OWNER_COMMANDS
    assert "/group-update" in OwnerCommandService.OWNER_COMMANDS
    assert "/faq-import" in OwnerCommandService.OWNER_COMMANDS


@pytest.mark.asyncio
async def test_user_help_lists_enabled_user_commands_only() -> None:
    class Catalog:
        async def list_commands(self):
            return [
                {"name": "/help", "description": "Show help.", "permissions": "user", "enabled": True},
                {"name": "/status", "description": "Status.", "permissions": "user", "enabled": False},
                {"name": "/system", "description": "System.", "permissions": "owner", "enabled": True},
            ]

    service = OwnerCommandService.__new__(OwnerCommandService)
    service.command_catalog = Catalog()

    async def not_owner(_message):
        return False

    service.is_owner_message = not_owner

    reply = await service._user_help(object())

    assert "/help - Show help." in reply
    assert "/status" not in reply
    assert "/system" not in reply


@pytest.mark.asyncio
async def test_owner_help_includes_enabled_admin_commands() -> None:
    class Catalog:
        async def list_commands(self):
            return [
                {"name": "/help", "description": "Show help.", "permissions": "user", "enabled": True},
                {"name": "/system", "description": "System.", "permissions": "owner", "enabled": True},
            ]

    service = OwnerCommandService.__new__(OwnerCommandService)
    service.command_catalog = Catalog()

    async def is_owner(_message):
        return True

    service.is_owner_message = is_owner

    reply = await service._user_help(object())

    assert "/help - Show help." in reply
    assert "/system - System." in reply


def test_parse_key_values_for_group_metadata() -> None:
    values = OwnerCommandService.parse_key_values(
        "community_name=Datacube Community\nowner_name=Fabian\npurpose=Testing\ntags=beta,zina,testing"
    )

    assert values["community_name"] == "Datacube Community"
    assert values["owner_name"] == "Fabian"
    assert values["purpose"] == "Testing"
    assert values["tags"] == "beta,zina,testing"


def test_extract_live_group_payload_from_waha_chat() -> None:
    service = OwnerCommandService.__new__(OwnerCommandService)
    payload = service._extract_live_group_payload(
        {
            "id": {"_serialized": "120363222222222222@g.us"},
            "name": "Datacube AU Testing",
            "participants": [{"id": "2348012345678@c.us"}],
            "description": "Testing group",
        }
    )

    assert payload is not None
    assert payload["chat_id"] == "120363222222222222@g.us"
    assert payload["group_name"] == "Datacube AU Testing"
    assert payload["participants_count"] == 1
    assert payload["description"] == "Testing group"

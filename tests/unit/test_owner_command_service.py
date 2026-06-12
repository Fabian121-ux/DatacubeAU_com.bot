from __future__ import annotations

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
    assert not OwnerCommandService.is_owner_id_static("15550000002@c.us", configured)


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

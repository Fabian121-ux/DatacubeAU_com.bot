from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.models.schema import AdminAccount, BotConfig, CommandCatalogEntry, Contact, OutboundMessage
from app.services.command_control_service import CommandControlService
from app.services.owner_management_command_service import OwnerManagementCommandService


OWNER_ID = "2348000000001@c.us"


def _event(body: str, *, message_id: str = "MGMT-1") -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": OWNER_ID,
            "from": OWNER_ID,
            "fromMe": True,
            "body": body,
        },
    }


async def _add_owner(db_session, *, permission: str = "owner") -> AdminAccount:
    owner = AdminAccount(
        name="Fabian",
        whatsapp_number="2348000000001",
        normalized_whatsapp_id=OWNER_ID,
        role="primary_admin",
        permission_level=permission,
        is_primary=True,
        is_enabled=True,
    )
    db_session.add(owner)
    await db_session.flush()
    return owner


async def _send(db_session, body: str, *, message_id: str = "MGMT-1"):
    message = MessageNormalizer().normalize(_event(body, message_id=message_id))
    return await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id=message_id,
        request_id=message_id,
    )


@pytest.mark.asyncio
async def test_listcommands_natural_alias_uses_existing_catalog_and_self_dm(db_session):
    await _add_owner(db_session)

    result = await _send(db_session, "@Zina listcommands")

    assert result is not None and result.consumed is True
    assert result.command == "/commands"
    assert "ZINA COMMANDS" in (result.reply_text or "")
    assert ".commands" in (result.reply_text or "")
    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == OWNER_ID


@pytest.mark.asyncio
async def test_cmdinfo_and_toggle_reuse_command_catalog(db_session):
    await _add_owner(db_session)

    info = await _send(db_session, ".cmd .sch", message_id="CMD-INFO")
    assert info is not None
    assert "COMMAND /schedule" in (info.reply_text or "")
    assert "Authority: OWNER" in (info.reply_text or "")
    assert "Handler: command_control:schedule" in (info.reply_text or "")

    disabled = await _send(db_session, ".cmdoff .sch", message_id="CMD-OFF")
    assert disabled is not None and "/schedule is now disabled" in (disabled.reply_text or "")
    schedule_row = (
        await db_session.execute(select(CommandCatalogEntry).where(CommandCatalogEntry.name == "/schedule"))
    ).scalar_one()
    assert schedule_row.is_enabled is False

    enabled = await _send(db_session, ".cmdon /schedule", message_id="CMD-ON")
    assert enabled is not None and "/schedule is now enabled" in (enabled.reply_text or "")
    await db_session.refresh(schedule_row)
    assert schedule_row.is_enabled is True


@pytest.mark.asyncio
async def test_management_recovery_commands_cannot_be_disabled_from_whatsapp(db_session):
    await _add_owner(db_session)

    result = await _send(db_session, ".cmdoff /cmdon")

    assert result is not None
    assert result.error is not None
    assert "cannot be disabled" in (result.reply_text or "")
    row = (
        await db_session.execute(select(CommandCatalogEntry).where(CommandCatalogEntry.name == "/cmdon"))
    ).scalar_one()
    assert row.is_enabled is True


@pytest.mark.asyncio
async def test_safe_config_allows_typed_values_and_blocks_secret_or_unknown_keys(db_session):
    await _add_owner(db_session)

    updated = await _send(
        db_session,
        ".config set auto_assist_inactivity_seconds 180",
        message_id="CFG-SET",
    )
    assert updated is not None and "180" in (updated.reply_text or "")
    row = (
        await db_session.execute(select(BotConfig).where(BotConfig.config_key == "auto_assist_inactivity_seconds"))
    ).scalar_one()
    assert row.config_value == "180"

    boolean = await _send(db_session, ".config set ai_enabled on", message_id="CFG-AI")
    assert boolean is not None and "ai_enabled = true" in (boolean.reply_text or "")

    secret = await _send(db_session, ".config get openrouter_api_key", message_id="CFG-SECRET")
    assert secret is not None and secret.error is not None
    assert "unknown or protected config key" in (secret.reply_text or "")
    assert "sk-" not in (secret.reply_text or "")

    invalid = await _send(
        db_session,
        ".config set auto_assist_inactivity_seconds 1",
        message_id="CFG-RANGE",
    )
    assert invalid is not None and invalid.error is not None
    assert "at least 5" in (invalid.reply_text or "")


@pytest.mark.asyncio
async def test_contact_inventory_classifies_saved_only_from_waha_saved_name_evidence(db_session):
    await _add_owner(db_session)
    db_session.add_all(
        [
            Contact(
                whatsapp_id="2348000000002@c.us",
                normalized_phone="2348000000002",
                contact_name="Amanda Christabel",
                push_name="Amanda",
                display_name="Amanda Christabel",
                identity_source="waha_contact_sync",
            ),
            Contact(
                whatsapp_id="2348000000003@c.us",
                normalized_phone="2348000000003",
                push_name="Peter",
                display_name="Peter",
                identity_source="inbound",
            ),
            Contact(
                whatsapp_id="120363000000000000@g.us",
                display_name="Test Group",
                identity_source="inbound",
            ),
        ]
    )
    await db_session.flush()

    summary = await _send(db_session, ".contacts", message_id="CONTACTS-SUMMARY")
    assert summary is not None
    assert "Known people: 2" in (summary.reply_text or "")
    assert "Saved: 1" in (summary.reply_text or "")
    assert "Unsaved: 1" in (summary.reply_text or "")

    saved = await _send(db_session, ".contacts saved 10", message_id="CONTACTS-SAVED")
    assert saved is not None
    assert "Amanda Christabel" in (saved.reply_text or "")
    assert "Peter" not in (saved.reply_text or "")

    unsaved = await _send(db_session, ".contacts unsaved 10", message_id="CONTACTS-UNSAVED")
    assert unsaved is not None
    assert "Peter" in (unsaved.reply_text or "")
    assert "Test Group" not in (unsaved.reply_text or "")


@pytest.mark.asyncio
async def test_contact_command_uses_ambiguity_safe_contact_intelligence(db_session):
    await _add_owner(db_session)
    db_session.add_all(
        [
            Contact(
                whatsapp_id="2348000000002@c.us",
                normalized_phone="2348000000002",
                contact_name="Amanda Christabel",
                display_name="Amanda Christabel",
                identity_source="waha_contact_sync",
            ),
            Contact(
                whatsapp_id="2348000000004@c.us",
                normalized_phone="2348000000004",
                contact_name="Amanda Christina",
                display_name="Amanda Christina",
                identity_source="waha_contact_sync",
            ),
        ]
    )
    await db_session.flush()

    ambiguous = await _send(db_session, ".contact Amanda", message_id="CONTACT-AMB")
    assert ambiguous is not None
    assert "ambiguous" in (ambiguous.reply_text or "").lower()
    assert "Amanda Christabel" in (ambiguous.reply_text or "")
    assert "Amanda Christina" in (ambiguous.reply_text or "")

    exact = await _send(db_session, ".contact Amanda Christabel", message_id="CONTACT-EXACT")
    assert exact is not None
    assert "Saved: yes" in (exact.reply_text or "")
    assert "2348000000002" in (exact.reply_text or "")
    assert "identity_json" not in (exact.reply_text or "")


@pytest.mark.asyncio
async def test_contactsync_delegates_to_existing_sync_service(db_session, monkeypatch):
    await _add_owner(db_session)
    calls = []

    async def fake_sync(self, *, session_name=None):
        calls.append(session_name)
        return {"fetched": 3, "created": 1, "updated": 1, "skipped": 1}

    monkeypatch.setattr(
        "app.services.owner_management_command_service.ContactSyncService.sync",
        fake_sync,
    )

    result = await _send(db_session, ".contactsync", message_id="CONTACT-SYNC")

    assert calls == [None]
    assert result is not None
    assert "Fetched: 3" in (result.reply_text or "")
    assert "Created: 1" in (result.reply_text or "")
    assert "Updated: 1" in (result.reply_text or "")
    assert "Skipped: 1" in (result.reply_text or "")


@pytest.mark.asyncio
async def test_management_service_denies_non_owner_without_side_effect(db_session):
    service = OwnerManagementCommandService(db_session)

    result = await service.handle("/config", "set ai_enabled on", permission="admin")

    assert result is not None and result.error == "owner permission required"
    rows = (
        await db_session.execute(select(BotConfig).where(BotConfig.config_key == "ai_enabled"))
    ).scalars().all()
    assert rows == []


def test_parser_accepts_bounded_natural_management_aliases_only_with_zina_prefix():
    assert CommandControlService.parse("@Zina listcommands") == (".commands", "")
    assert CommandControlService.parse("@Zina list commands") == (".commands", "")
    assert CommandControlService.parse("@Zina list contacts") == (".contacts", "")
    assert CommandControlService.parse("listcommands") is None

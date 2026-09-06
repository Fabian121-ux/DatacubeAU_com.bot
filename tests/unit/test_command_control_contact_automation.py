from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.models.schema import AdminAccount, OutboundMessage
from app.services.command_control_service import CommandControlService


def _event(body: str, *, chat_id: str = "2348000000001@c.us", message_id: str = "AUTOMATION-CMD-1") -> dict:
    return {
        "event": "message.any",
        "session": "default",
        "payload": {
            "id": message_id,
            "chatId": chat_id,
            "from": chat_id,
            "fromMe": True,
            "body": body,
        },
    }


def _admin(*, permission: str = "owner", primary: bool = True, number: str = "2348000000001") -> AdminAccount:
    return AdminAccount(
        name="Fabian" if primary else "Admin",
        whatsapp_number=number,
        normalized_whatsapp_id=f"{number}@c.us",
        role="primary_admin" if primary else "admin",
        permission_level=permission,
        is_primary=primary,
        is_enabled=True,
    )


def test_command_center_owns_contact_automation_aliases():
    assert CommandControlService._contact_automation_action(
        ".automation", "set 17 2348000000999@c.us conversational"
    ) == ("set", "17 2348000000999@c.us conversational")
    assert CommandControlService._contact_automation_action(
        ".automation", "disable 18 2348000000888@c.us"
    ) == ("disable", "18 2348000000888@c.us")
    assert CommandControlService._contact_automation_action(
        ".automation-set", "19 2348000000777@c.us support,followup"
    ) == ("set", "19 2348000000777@c.us support,followup")
    assert CommandControlService._contact_automation_action(
        ".automation-disable", "20 2348000000666@c.us"
    ) == ("disable", "20 2348000000666@c.us")
    assert CommandControlService._contact_automation_action(".not-automation", "20") == (None, "20")


@pytest.mark.asyncio
async def test_owner_self_dm_contact_automation_delegates_exact_identity(db_session, monkeypatch):
    owner = _admin()
    db_session.add(owner)
    await db_session.flush()

    calls: list[dict] = []

    class FakePolicyCommands:
        ACTIONS = frozenset({"set", "disable"})

        def __init__(self, session):
            assert session is db_session

        async def handle(self, action, args, *, permission, owner_identity):
            calls.append(
                {
                    "action": action,
                    "args": args,
                    "permission": permission,
                    "owner_identity": owner_identity,
                }
            )
            return SimpleNamespace(
                consumed=True,
                reply_text="Contact automation updated.",
                error=None,
                policy_id=31,
            )

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerContactAutomationPolicyCommandService", FakePolicyCommands)

    body = ".automation set 17 2348000000999@c.us conversational,followup"
    message = MessageNormalizer().normalize(_event(body))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="AUTOMATION-CMD-1",
        request_id="AUTOMATION-CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command == ".automation"
    assert result.reply_text == "Contact automation updated."
    assert calls == [
        {
            "action": "set",
            "args": "17 2348000000999@c.us conversational,followup",
            "permission": "owner",
            "owner_identity": f"admin:{owner.id}",
        }
    ]

    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == owner.normalized_whatsapp_id
    assert queued[0].message_text == "Contact automation updated."
    # The owner payload binding is added by the producer; assert the producer
    # metadata exactly and that the row is bound to its authorized content.
    metadata = dict(queued[0].formatting_json)
    assert metadata.pop(OutboundAuthorizationService.OWNER_PAYLOAD_KEY, None)
    assert metadata == {"source": "command_control", "command": ".automation"}
    assert OutboundAuthorizationService.owner_payload_matches(queued[0])


@pytest.mark.asyncio
async def test_admin_peer_dm_cannot_reach_contact_automation_policy_mutation(db_session, monkeypatch):
    owner = _admin()
    admin = _admin(permission="admin", primary=False, number="2348000000003")
    db_session.add_all([owner, admin])
    await db_session.flush()

    called = False

    class ExplodingPolicyCommands:
        ACTIONS = frozenset({"set", "disable"})

        def __init__(self, session):
            nonlocal called
            called = True
            raise AssertionError("ADMIN must not enter OWNER contact automation adapter")

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerContactAutomationPolicyCommandService", ExplodingPolicyCommands)

    message = MessageNormalizer().normalize(
        _event(
            ".automation set 17 2348000000999@c.us conversational",
            chat_id=admin.normalized_whatsapp_id,
            message_id="ADMIN-AUTOMATION",
        )
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="ADMIN-AUTOMATION",
        request_id="ADMIN-AUTOMATION",
    )

    assert result is None
    assert called is False
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []


@pytest.mark.asyncio
async def test_unregistered_from_me_identity_cannot_reach_contact_automation_policy_mutation(db_session, monkeypatch):
    owner = _admin()
    db_session.add(owner)
    await db_session.flush()

    called = False

    class ExplodingPolicyCommands:
        ACTIONS = frozenset({"set", "disable"})

        def __init__(self, session):
            nonlocal called
            called = True
            raise AssertionError("unregistered identity must not enter OWNER contact automation adapter")

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerContactAutomationPolicyCommandService", ExplodingPolicyCommands)

    outsider = "2348000000099@c.us"
    message = MessageNormalizer().normalize(
        _event(
            ".automation disable 17 2348000000999@c.us",
            chat_id=outsider,
            message_id="USER-AUTOMATION",
        )
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="USER-AUTOMATION",
        request_id="USER-AUTOMATION",
    )

    assert result is not None and result.consumed is True
    assert result.error == "owner authorization failed"
    assert called is False
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []

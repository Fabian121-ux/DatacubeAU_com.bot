from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import select

from app.core.message_normalizer import MessageNormalizer
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.models.schema import AdminAccount, OutboundMessage
from app.services.command_control_service import CommandControlService


def _event(body: str, *, chat_id: str = "2348000000001@c.us", message_id: str = "APPROVAL-CMD-1") -> dict:
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


def test_command_center_owns_namespaced_outbound_approval_aliases():
    assert CommandControlService._outbound_approval_action(".approval", "17") == ("info", "17")
    assert CommandControlService._outbound_approval_action(".approval", "approve 18") == ("approve", "18")
    assert CommandControlService._outbound_approval_action(".approve", "19") == ("approve", "19")
    assert CommandControlService._outbound_approval_action(".approval-edit", "20 replacement") == (
        "edit",
        "20 replacement",
    )
    assert CommandControlService._outbound_approval_action(".approval-reject", "21") == ("reject", "21")
    assert CommandControlService._outbound_approval_action(".approval-requeue", "22") == ("requeue", "22")
    assert CommandControlService._outbound_approval_action(".not-an-approval", "22") == (None, "22")


@pytest.mark.asyncio
async def test_owner_self_dm_approval_alias_delegates_exact_action_and_preserves_formatting(db_session, monkeypatch):
    owner = _admin()
    db_session.add(owner)
    await db_session.flush()

    calls: list[dict] = []

    class FakeApprovalCommands:
        ACTIONS = frozenset({"info", "approve", "edit", "reject", "requeue"})

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
                reply_text="Approval updated.",
                error=None,
                approval_id=20,
                outbound_queue_id=44,
            )

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerOutboundApprovalCommandService", FakeApprovalCommands)

    body = ".approval edit 20 > quoted context\n\n*Approved exact text* with `code`"
    message = MessageNormalizer().normalize(_event(body))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="APPROVAL-CMD-1",
        request_id="APPROVAL-CMD-1",
    )

    assert result is not None and result.consumed is True
    assert result.command == ".approval"
    assert result.reply_text == "Approval updated."
    assert calls == [
        {
            "action": "edit",
            "args": "20 > quoted context\n\n*Approved exact text* with `code`",
            "permission": "owner",
            "owner_identity": f"admin:{owner.id}",
        }
    ]

    queued = (await db_session.execute(select(OutboundMessage))).scalars().all()
    assert len(queued) == 1
    assert queued[0].chat_id == owner.normalized_whatsapp_id
    assert queued[0].message_text == "Approval updated."
    # The owner payload binding is added by the producer; assert the producer
    # metadata exactly and that the row is bound to its authorized content.
    metadata = dict(queued[0].formatting_json)
    assert metadata.pop(OutboundAuthorizationService.OWNER_PAYLOAD_KEY, None)
    assert metadata == {"source": "command_control", "command": ".approval"}
    assert OutboundAuthorizationService.owner_payload_matches(queued[0])


@pytest.mark.asyncio
async def test_admin_peer_dm_cannot_reach_outbound_approval_mutation(db_session, monkeypatch):
    owner = _admin()
    admin = _admin(permission="admin", primary=False, number="2348000000003")
    db_session.add_all([owner, admin])
    await db_session.flush()

    called = False

    class ExplodingApprovalCommands:
        ACTIONS = frozenset({"info", "approve", "edit", "reject", "requeue"})

        def __init__(self, session):
            nonlocal called
            called = True
            raise AssertionError("ADMIN must not enter OWNER approval adapter")

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerOutboundApprovalCommandService", ExplodingApprovalCommands)

    message = MessageNormalizer().normalize(
        _event(".approve 17", chat_id=admin.normalized_whatsapp_id, message_id="ADMIN-APPROVAL")
    )
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="ADMIN-APPROVAL",
        request_id="ADMIN-APPROVAL",
    )

    assert result is None
    assert called is False
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []


@pytest.mark.asyncio
async def test_unregistered_from_me_identity_cannot_reach_outbound_approval_mutation(db_session, monkeypatch):
    owner = _admin()
    db_session.add(owner)
    await db_session.flush()

    called = False

    class ExplodingApprovalCommands:
        ACTIONS = frozenset({"info", "approve", "edit", "reject", "requeue"})

        def __init__(self, session):
            nonlocal called
            called = True
            raise AssertionError("unregistered identity must not enter OWNER approval adapter")

    import app.services.command_control_service as command_module

    monkeypatch.setattr(command_module, "OwnerOutboundApprovalCommandService", ExplodingApprovalCommands)

    outsider = "2348000000099@c.us"
    message = MessageNormalizer().normalize(_event(".approve 17", chat_id=outsider, message_id="USER-APPROVAL"))
    result = await CommandControlService(db_session).handle_from_me(
        message,
        transport_message_id="USER-APPROVAL",
        request_id="USER-APPROVAL",
    )

    assert result is not None and result.consumed is True
    assert result.error == "owner authorization failed"
    assert called is False
    assert (await db_session.execute(select(OutboundMessage))).scalars().all() == []

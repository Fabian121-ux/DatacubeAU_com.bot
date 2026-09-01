from types import SimpleNamespace

import pytest

from app.services.owner_outbound_approval_command_service import OwnerOutboundApprovalCommandService


class FakeMutations:
    def __init__(self):
        self.calls = []

    async def inspect(self, approval_id):
        self.calls.append(("info", approval_id))
        return SimpleNamespace(reply_text="info ok", error=None, outbound_queue_id=91)

    async def approve(self, approval_id, *, owner_identity):
        self.calls.append(("approve", approval_id, owner_identity))
        return SimpleNamespace(reply_text="approve ok", error=None, outbound_queue_id=92)

    async def edit(self, approval_id, new_text):
        self.calls.append(("edit", approval_id, new_text))
        return SimpleNamespace(reply_text="edit ok", error=None, outbound_queue_id=93)

    async def reject(self, approval_id):
        self.calls.append(("reject", approval_id))
        return SimpleNamespace(reply_text="reject ok", error=None, outbound_queue_id=94)

    async def requeue(self, approval_id):
        self.calls.append(("requeue", approval_id))
        return SimpleNamespace(reply_text="requeue ok", error=None, outbound_queue_id=95)


@pytest.mark.asyncio
@pytest.mark.parametrize("permission", ["user", "admin", "", "ADMIN"])
async def test_non_owner_permission_cannot_reach_mutation_service(permission):
    mutations = FakeMutations()
    service = OwnerOutboundApprovalCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "approve",
        "41",
        permission=permission,
        owner_identity="admin@example.invalid",
    )

    assert result.consumed is True
    assert result.error == "owner permission required"
    assert result.reply_text == "Owner command. Access denied."
    assert mutations.calls == []


@pytest.mark.asyncio
async def test_owner_approve_delegates_exact_id_and_bounded_identity():
    mutations = FakeMutations()
    service = OwnerOutboundApprovalCommandService(None, mutation_service=mutations)
    owner_identity = "o" * 300

    result = await service.handle(
        "approve",
        "41",
        permission="OWNER",
        owner_identity=owner_identity,
    )

    assert result.error is None
    assert result.approval_id == 41
    assert result.outbound_queue_id == 92
    assert mutations.calls == [("approve", 41, "o" * 160)]


@pytest.mark.asyncio
async def test_owner_edit_requires_exact_id_and_replacement_text():
    mutations = FakeMutations()
    service = OwnerOutboundApprovalCommandService(None, mutation_service=mutations)

    missing_text = await service.handle(
        "edit",
        "41",
        permission="owner",
        owner_identity="owner",
    )
    assert missing_text.error == "invalid approval command arguments"
    assert mutations.calls == []

    result = await service.handle(
        "edit",
        "41 Keep *this* formatting and `code`\n\n> quoted line",
        permission="owner",
        owner_identity="owner",
    )
    assert result.error is None
    assert mutations.calls == [("edit", 41, "Keep *this* formatting and `code`\n\n> quoted line")]


@pytest.mark.asyncio
@pytest.mark.parametrize("args", ["0", "-1", "abc", "41 extra"])
async def test_non_edit_actions_require_one_positive_exact_id(args):
    mutations = FakeMutations()
    service = OwnerOutboundApprovalCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "reject",
        args,
        permission="owner",
        owner_identity="owner",
    )

    assert result.error == "invalid approval command arguments"
    assert mutations.calls == []


@pytest.mark.asyncio
async def test_unsupported_action_is_not_consumed_and_never_mutates():
    mutations = FakeMutations()
    service = OwnerOutboundApprovalCommandService(None, mutation_service=mutations)

    result = await service.handle(
        "broadcast",
        "41",
        permission="owner",
        owner_identity="owner",
    )

    assert result.consumed is False
    assert result.error == "unsupported approval action"
    assert mutations.calls == []

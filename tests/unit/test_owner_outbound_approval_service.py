from datetime import timedelta
from types import SimpleNamespace

import pytest

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.owner_outbound_approval_service import OwnerOutboundApprovalService
from app.utils.time import utcnow


class _Result:
    def __init__(self, scalar=None):
        self._scalar = scalar

    def scalar_one_or_none(self):
        return self._scalar


class _Session:
    def __init__(self, scalars=None):
        self.scalars = list(scalars or [])
        self.calls = []

    async def execute(self, statement, params=None):
        self.calls.append((str(statement), params or {}))
        scalar = self.scalars.pop(0) if self.scalars else None
        return _Result(scalar)


def _row(*, approval_status="pending", queue_status="deferred", text_value="hello"):
    digest = OutboundAuthorizationService.content_hash(text_value)
    return {
        "id": 41,
        "inbound_message_id": 5,
        "outbound_queue_id": 10,
        "target_chat_id": "222@c.us",
        "content_sha256": digest,
        "status": approval_status,
        "expires_at": utcnow() + timedelta(minutes=10),
        "queue_chat_id": "222@c.us",
        "message_text": text_value,
        "queue_status": queue_status,
        "formatting_json": {
            "inbound_message_id": 5,
            "contact_id": 7,
            "content_sha256": digest,
            "response_category": "normal_reply",
            "delivery_policy": "approval_required",
        },
    }


def test_authority_mismatch_accepts_only_exact_durable_binding():
    assert OwnerOutboundApprovalService._authority_mismatch(_row()) is None

    wrong_target = _row()
    wrong_target["queue_chat_id"] = "333@c.us"
    assert "target" in OwnerOutboundApprovalService._authority_mismatch(wrong_target)

    changed_content = _row()
    changed_content["message_text"] = "changed"
    assert "content hash" in OwnerOutboundApprovalService._authority_mismatch(changed_content)

    missing_source = _row()
    missing_source["formatting_json"].pop("inbound_message_id")
    assert "missing durable" in OwnerOutboundApprovalService._authority_mismatch(missing_source)


@pytest.mark.asyncio
async def test_approve_requeues_only_exact_deferred_row_after_owner_approval(monkeypatch):
    session = _Session(scalars=[10, None])
    service = OwnerOutboundApprovalService(session)
    row = _row()

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.approve(41, owner_identity="owner@c.us")

    assert result.ok is True
    assert result.outbound_queue_id == 10
    assert any("SET status = 'approved'" in sql for sql, _ in session.calls)
    assert any("SET status = 'pending'" in sql and params.get("queue_id") == 10 for sql, params in session.calls)


@pytest.mark.asyncio
async def test_approve_fails_closed_on_wrong_target_without_granting_authority(monkeypatch):
    session = _Session()
    service = OwnerOutboundApprovalService(session)
    row = _row()
    row["queue_chat_id"] = "wrong@c.us"

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.approve(41, owner_identity="owner@c.us")

    assert result.ok is False
    assert "authority" in result.reply_text.lower()
    assert not any("SET status = 'approved'" in sql for sql, _ in session.calls)


@pytest.mark.asyncio
async def test_edit_rebinds_hash_but_keeps_draft_deferred_and_pending(monkeypatch):
    session = _Session()
    service = OwnerOutboundApprovalService(session)
    row = _row()

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.edit(41, "new exact text")
    expected = OutboundAuthorizationService.content_hash("new exact text")

    assert result.ok is True
    assert "still requires owner approval" in result.reply_text.lower()
    assert any(
        "UPDATE outbound_queue" in sql
        and params.get("message_text") == "new exact text"
        and expected in params.get("formatting_json", "")
        for sql, params in session.calls
    )
    assert any(
        "UPDATE outbound_approvals" in sql and params.get("content_sha256") == expected
        for sql, params in session.calls
    )
    assert not any("SET status = 'approved'" in sql for sql, _ in session.calls)


@pytest.mark.asyncio
async def test_requeue_refuses_sent_or_unapproved_rows(monkeypatch):
    service = OwnerOutboundApprovalService(_Session())

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_lock", _noop)
    monkeypatch.setattr(service, "_audit", _noop)

    async def _sent(*args, **kwargs):
        return _row(approval_status="approved", queue_status="sent")

    monkeypatch.setattr(service, "_load_exact", _sent)
    sent = await service.requeue(41)
    assert sent.ok is False
    assert "sent" in sent.reply_text

    async def _pending(*args, **kwargs):
        return _row(approval_status="pending", queue_status="deferred")

    monkeypatch.setattr(service, "_load_exact", _pending)
    pending = await service.requeue(41)
    assert pending.ok is False
    assert "already-approved" in pending.reply_text


@pytest.mark.asyncio
async def test_reject_never_turns_row_sendable(monkeypatch):
    session = _Session(scalars=[10, None])
    service = OwnerOutboundApprovalService(session)
    row = _row()

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.reject(41)

    assert result.ok is True
    assert any("SET status = 'rejected'" in sql for sql, _ in session.calls)
    assert any("SET status = 'deferred'" in sql for sql, _ in session.calls)
    assert not any("SET status = 'pending'" in sql for sql, _ in session.calls)

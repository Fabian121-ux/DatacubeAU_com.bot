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


def _row(
    *,
    approval_status="pending",
    queue_status="deferred",
    text_value="hello",
    media_url=None,
    media_type=None,
    media_caption=None,
    media_mime=None,
    media_filename=None,
):
    formatting = {
        "inbound_message_id": 5,
        "contact_id": 7,
        "response_category": "normal_reply",
        "delivery_policy": "approval_required",
    }
    if media_mime is not None:
        formatting["media_mime"] = media_mime
    if media_filename is not None:
        formatting["media_filename"] = media_filename
    digest = OutboundAuthorizationService.content_hash_for_fields(
        text_value,
        media_url=media_url,
        media_type=media_type,
        media_caption=media_caption,
        formatting_json=formatting,
    )
    formatting["content_sha256"] = digest
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
        "media_url": media_url,
        "media_type": media_type,
        "media_caption": media_caption,
        "queue_status": queue_status,
        "formatting_json": formatting,
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


@pytest.mark.parametrize(
    ("field", "mutated_value"),
    [("media_mime", "image/png"), ("media_filename", "renamed.jpg")],
)
def test_authority_mismatch_binds_transport_metadata(field, mutated_value):
    row = _row(
        media_url="http://waha:3000/api/files/original.jpg",
        media_type="image",
        media_caption="original caption",
        media_mime="image/jpeg",
        media_filename="original.jpg",
    )
    assert OwnerOutboundApprovalService._authority_mismatch(row) is None

    mutated = {**row, "formatting_json": dict(row["formatting_json"])}
    mutated["formatting_json"][field] = mutated_value
    assert "content hash" in OwnerOutboundApprovalService._authority_mismatch(mutated)


@pytest.mark.asyncio
async def test_approve_requeues_only_exact_deferred_row_after_owner_approval(monkeypatch):
    session = _Session(scalars=[10, None])
    service = OwnerOutboundApprovalService(session)
    row = _row()

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
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

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.approve(41, owner_identity="owner@c.us")

    assert result.ok is False
    assert "authority" in result.reply_text.lower()
    assert not any("SET status = 'approved'" in sql for sql, _ in session.calls)


@pytest.mark.asyncio
async def test_edit_rebinds_hash_but_keeps_draft_deferred_and_pending(monkeypatch):
    session = _Session(scalars=[None, 41])
    service = OwnerOutboundApprovalService(session)
    row = _row()

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
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
async def test_edit_rebinds_media_digest_including_transport_metadata(monkeypatch):
    session = _Session(scalars=[None, 41])
    service = OwnerOutboundApprovalService(session)
    row = _row(
        media_url="http://waha:3000/api/files/original.jpg",
        media_type="image",
        media_caption="original caption",
        media_mime="image/jpeg",
        media_filename="original.jpg",
    )

    async def _noop(*args, **kwargs):
        return None

    async def _load(*args, **kwargs):
        return row

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.edit(41, "edited exact text")
    expected = OutboundAuthorizationService.content_hash_for_fields(
        "edited exact text",
        media_url=row["media_url"],
        media_type=row["media_type"],
        media_caption=row["media_caption"],
        formatting_json=row["formatting_json"],
    )

    assert result.ok is True
    assert any(
        "UPDATE outbound_queue" in sql
        and params.get("message_text") == "edited exact text"
        and expected in params.get("formatting_json", "")
        for sql, params in session.calls
    )
    assert any(
        "UPDATE outbound_approvals" in sql and params.get("content_sha256") == expected
        for sql, params in session.calls
    )


@pytest.mark.asyncio
async def test_requeue_refuses_sent_or_unapproved_rows(monkeypatch):
    service = OwnerOutboundApprovalService(_Session())

    async def _noop(*args, **kwargs):
        return None

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
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

    monkeypatch.setattr(service, "_lock_queue_then_approval", _noop)
    monkeypatch.setattr(service, "_load_exact", _load)
    monkeypatch.setattr(service, "_audit", _noop)

    result = await service.reject(41)

    assert result.ok is True
    assert any("SET status = 'rejected'" in sql for sql, _ in session.calls)
    assert any("SET status = 'deferred'" in sql for sql, _ in session.calls)
    assert not any("SET status = 'pending'" in sql for sql, _ in session.calls)

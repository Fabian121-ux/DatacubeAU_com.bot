from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, status

from app.api import inbound
from app.db import SessionLocal
from app.services.deleted_message_service import DeletedMessageService
from app.services.inbound_idempotency_service import InboundIdempotencyService, InboundReceipt
from app.services.logging_service import log_event


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/waha-events", status_code=status.HTTP_202_ACCEPTED)
async def waha_events_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    """WAHA event gateway that adds durable revoke handling without duplicating message routing.

    Normal `message`/`message.any` traffic delegates to the established inbound webhook.
    Only `message.revoked` is handled here. For an accepted normal message, reconciliation
    is appended to the same BackgroundTasks queue *after* the established inbound task,
    so an earlier unmatched revoke is checked only after the original Message had a chance
    to persist. This closes the revoke-before-message-commit race without synthesizing content.
    """
    try:
        event = await request.json()
    except Exception:  # noqa: BLE001
        return await inbound.waha_webhook(request, background_tasks)
    if not isinstance(event, dict):
        return await inbound.waha_webhook(request, background_tasks)

    event_name = inbound._resolve_event_name(event)
    if event_name != "message.revoked":
        response = await inbound.waha_webhook(request, background_tasks)
        if event_name in {"message", "message.any"} and response.get("status") == "accepted":
            payload = inbound._resolve_payload(event)
            source_message_id = inbound._resolve_message_id(payload)
            chat_id = inbound._resolve_chat_id(payload)
            if source_message_id:
                # `inbound.waha_webhook` already appended its persistence/routing task.
                # Starlette executes BackgroundTasks in insertion order, so this check
                # runs afterwards instead of racing the original Message commit.
                background_tasks.add_task(
                    _reconcile_after_message,
                    source_message_id,
                    chat_id,
                )
        return response

    if not inbound._webhook_authenticated(request):
        log_event(logger, logging.WARNING, "webhook_ignored", reason="unauthorized_webhook", event_name=event_name)
        return {"status": "ignored", "reason": "unauthorized_webhook", "event_name": event_name}

    payload = inbound._resolve_payload(event)
    if not inbound._session_matches_config(event, payload):
        log_event(logger, logging.WARNING, "webhook_ignored", reason="unexpected_session", event_name=event_name)
        return {"status": "ignored", "reason": "unexpected_session", "event_name": event_name}

    revoked_id = DeletedMessageService._revoked_message_id(payload)
    request_id = (
        request.headers.get("x-webhook-request-id")
        or request.headers.get("x-request-id")
        or str(event.get("id") or "").strip()
        or revoked_id
        or "waha-revocation"
    )
    if not revoked_id:
        log_event(logger, logging.WARNING, "webhook_ignored", request_id=request_id, event_name=event_name, reason="missing_revoked_message_id")
        return {"status": "ignored", "reason": "missing_revoked_message_id", "event_name": event_name}

    session_name = inbound._resolve_session_name(event, payload) or "default"
    event_key = f"{session_name}:message.revoked:{revoked_id}"
    receipt = InboundReceipt(
        event_key=event_key,
        session_name=session_name,
        chat_id=DeletedMessageService._revoked_chat_id(payload),
        message_id=revoked_id,
    )

    async with SessionLocal() as db:
        claimed = await InboundIdempotencyService(db).claim(receipt)
    if not claimed:
        return {
            "status": "duplicate",
            "request_id": request_id,
            "event_name": event_name,
            "message_id": revoked_id,
        }

    try:
        async with SessionLocal() as db:
            result = await DeletedMessageService(db).record_revocation(event)
            await InboundIdempotencyService(db).mark_completed(event_key, commit=False)
            await db.commit()
    except Exception:  # noqa: BLE001
        async with SessionLocal() as db:
            await InboundIdempotencyService(db).release_failed(event_key)
        raise

    log_event(
        logger,
        logging.INFO,
        "message_revocation_processed",
        request_id=request_id,
        event_name=event_name,
        revoked_message_id=revoked_id,
        matched=bool(result and result.matched),
        changed=bool(result and result.changed),
    )
    return {
        "status": "accepted",
        "reason": "message_revoked",
        "request_id": request_id,
        "event_name": event_name,
        "message_id": revoked_id,
        "matched": bool(result and result.matched),
        "changed": bool(result and result.changed),
    }


async def _reconcile_after_message(source_message_id: str, chat_id: str | None) -> None:
    """Reconcile a prior unmatched revoke after normal inbound persistence completes."""
    async with SessionLocal() as db:
        reconciled = await DeletedMessageService(db).reconcile_pending_for_message(
            source_message_id=source_message_id,
            chat_id=chat_id,
        )
        if reconciled:
            await db.commit()
            log_event(
                logger,
                logging.INFO,
                "message_revocation_late_reconciled",
                message_id=source_message_id,
                chat_id=chat_id,
            )
        else:
            await db.rollback()

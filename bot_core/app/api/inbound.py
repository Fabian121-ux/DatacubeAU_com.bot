from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, status

from app.core.router import InboundRouter
from app.db import SessionLocal
from app.services.logging_service import log_event


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/waha", status_code=status.HTTP_202_ACCEPTED)
async def waha_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    # Parse body defensively — never return 422 to WAHA or it retries aggressively
    try:
        event = await request.json()
    except Exception:  # noqa: BLE001
        log_event(logger, logging.WARNING, "webhook_ignored", reason="invalid_json")
        return {"status": "ignored", "reason": "invalid_json"}

    if not isinstance(event, dict):
        log_event(logger, logging.WARNING, "webhook_ignored", reason="not_object")
        return {"status": "ignored", "reason": "not_object"}

    event_name = _resolve_event_name(event)
    payload = _resolve_payload(event)
    message_id = _resolve_message_id(payload)
    request_id = (
        request.headers.get("x-webhook-request-id")
        or request.headers.get("x-request-id")
        or message_id
        or "waha-webhook"
    )

    if event_name and event_name not in {"message", "message.any"}:
        log_event(
            logger,
            logging.INFO,
            "webhook_ignored",
            request_id=request_id,
            event_name=event_name,
            reason="unsupported_event",
        )
        return {"status": "ignored", "reason": "unsupported_event", "event_name": event_name}

    if _is_from_me(payload):
        log_event(
            logger,
            logging.INFO,
            "webhook_ignored",
            request_id=request_id,
            event_name=event_name or "message",
            message_id=message_id,
            reason="from_me",
        )
        return {"status": "ignored", "reason": "from_me", "event_name": event_name or "message"}

    background_tasks.add_task(_process_event_async, event, request_id)
    log_event(
        logger,
        logging.INFO,
        "webhook_queued",
        request_id=request_id,
        event_name=event_name or "message",
        message_id=message_id,
    )
    return {
        "status": "accepted",
        "request_id": request_id,
        "event_name": event_name or "message",
        "message_id": message_id,
    }


async def _process_event_async(event: dict[str, Any], request_id: str) -> None:
    async with SessionLocal() as db:
        inbound_router = InboundRouter(db)
        result: dict[str, Any] | None = None
        error_text: str | None = None
        try:
            result = await inbound_router.process_event(event)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            error_text = str(exc)
            log_event(logger, logging.ERROR, "webhook_processing_failed", request_id=request_id, error=error_text)
            logger.exception("WAHA inbound processing failed")
        finally:
            await inbound_router.close()

        log_event(
            logger,
            logging.INFO if error_text is None else logging.ERROR,
            "webhook_processing_completed",
            request_id=request_id,
            status=result.get("status") if result else "error",
            action=result.get("action") if result else None,
            inbound_message_id=result.get("inbound_message_id") if result else None,
            outbound_message_id=result.get("outbound_message_id") if result else None,
            error=error_text,
        )


def _resolve_event_name(event: dict[str, Any]) -> str | None:
    raw_name = event.get("event")
    if isinstance(raw_name, str) and raw_name.strip():
        return raw_name.strip().lower()
    return None


def _resolve_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = event.get("payload")
    if isinstance(payload, dict):
        return payload
    return event


def _resolve_message_id(payload: dict[str, Any]) -> str | None:
    nested_message = payload.get("message")
    nested_message_id = nested_message.get("id") if isinstance(nested_message, dict) else None
    raw_message_id = payload.get("id") or nested_message_id
    if raw_message_id is None:
        return None
    text = str(raw_message_id).strip()
    return text or None


def _is_from_me(payload: dict[str, Any]) -> bool:
    raw_value = payload.get("fromMe")
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"1", "true", "yes"}
    return False

from __future__ import annotations

import logging
import hashlib
import json
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy import select, update

from fastapi.responses import JSONResponse
import hmac

from app.core.router import InboundRouter
from app.config import settings
from app.db import SessionLocal
from app.services.logging_service import log_event
from app.models.schema import InboundEvent, OutboundMessage


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/waha", status_code=status.HTTP_200_OK)
async def waha_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    raw_body = await request.body()

    if settings.whatsapp_hook_hmac_key:
        signature = request.headers.get("x-webhook-hmac")
        algorithm = request.headers.get("x-webhook-hmac-algorithm")
        
        if not signature:
            log_event(logger, logging.WARNING, "webhook_ignored", reason="missing_hmac_signature")
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"status": "ignored", "reason": "missing_hmac_signature"})
            
        if algorithm and algorithm.lower() != "sha512":
            log_event(logger, logging.WARNING, "webhook_ignored", reason="unsupported_hmac_algorithm")
            return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "ignored", "reason": "unsupported_hmac_algorithm"})
            
        expected = hmac.new(
            settings.whatsapp_hook_hmac_key.encode("utf-8"),
            raw_body,
            hashlib.sha512
        ).hexdigest()
        
        if not hmac.compare_digest(signature, expected):
            log_event(logger, logging.WARNING, "webhook_ignored", reason="invalid_hmac_signature")
            return JSONResponse(status_code=status.HTTP_401_UNAUTHORIZED, content={"status": "ignored", "reason": "invalid_hmac_signature"})

    try:
        event = json.loads(raw_body)
    except Exception:  # noqa: BLE001
        log_event(logger, logging.WARNING, "webhook_ignored", reason="invalid_json")
        return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content={"status": "ignored", "reason": "invalid_json"})

    if not isinstance(event, dict):
        log_event(logger, logging.WARNING, "webhook_ignored", reason="not_object")
        return {"status": "ignored", "reason": "not_object"}

    event_name = _resolve_event_name(event)
    payload = _resolve_payload(event)
    message_id = _resolve_message_id(payload)
    session_name = event.get("session") or "default"
    
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

    if not message_id:
        log_event(logger, logging.WARNING, "webhook_ignored", request_id=request_id, reason="missing_message_id")
        return {"status": "ignored", "reason": "missing_message_id"}

    payload_hash = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()

    async with SessionLocal() as db:
        if _is_from_me(payload):
            stmt = select(OutboundMessage).where(OutboundMessage.waha_message_id == message_id)
            result = await db.execute(stmt)
            outbound_match = result.scalar_one_or_none()
            if outbound_match or event_name == "message.any":
                log_event(
                    logger,
                    logging.INFO,
                    "webhook_ignored",
                    request_id=request_id,
                    event_name=event_name or "message",
                    message_id=message_id,
                    reason="outbound_echo",
                )
                return {"status": "ignored", "reason": "outbound_echo", "event_name": event_name or "message"}

        from sqlalchemy.dialects.postgresql import insert
        from sqlalchemy.exc import OperationalError
        
        try:
            stmt = insert(InboundEvent).values(
                provider="waha",
                session_name=session_name,
                event_type=event_name or "message",
                provider_message_id=message_id,
                payload_hash=payload_hash,
                processing_status="received"
            ).on_conflict_do_nothing()
            await db.execute(stmt)
            await db.commit()
        except Exception:
            await db.rollback()

        claim_stmt = (
            select(InboundEvent)
            .where(InboundEvent.provider_message_id == message_id)
            .where(InboundEvent.provider == "waha")
            .with_for_update(nowait=True)
        )
        try:
            event_record = (await db.execute(claim_stmt)).scalar_one_or_none()
        except OperationalError:
            await db.rollback()
            log_event(logger, logging.INFO, "webhook_ignored", request_id=request_id, reason="duplicate_event_locked")
            return {"status": "ignored", "reason": "duplicate_event_locked"}
            
        if not event_record:
            await db.rollback()
            return {"status": "ignored", "reason": "missing_event"}
            
        event_record.delivery_attempt_count += 1
        
        event_status = event_record.processing_status
        if event_status in ("processing", "completed", "ignored", "failed_final"):
            await db.commit()
            log_event(logger, logging.INFO, "webhook_ignored", request_id=request_id, reason=f"duplicate_event_{event_status}")
            return {"status": "ignored", "reason": f"duplicate_event_{event_status}"}
            
        event_record.processing_status = "processing"
        await db.commit()

    background_tasks.add_task(_process_event_async, event, request_id, message_id)
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


async def _process_event_async(event: dict[str, Any], request_id: str, message_id: str) -> None:
    async with SessionLocal() as db:
        inbound_router = InboundRouter(db)
        result: dict[str, Any] | None = None
        error_text: str | None = None
        try:
            result = await inbound_router.process_event(event)
            await db.execute(
                update(InboundEvent)
                .where(InboundEvent.provider_message_id == message_id)
                .values(processing_status="completed")
            )
            await db.commit()
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            error_text = str(exc)
            await db.execute(
                update(InboundEvent)
                .where(InboundEvent.provider_message_id == message_id)
                .values(processing_status="failed_retryable", processing_error=error_text)
            )
            await db.commit()
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

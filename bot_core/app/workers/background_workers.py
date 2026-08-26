from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.models.schema import AuditLog, OutboundMessage, WahaOutage
from app.services.conversation_open_loop_service import ConversationOpenLoopService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.logging_service import log_event
from app.services.scheduled_action_service import ScheduledActionService
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.time import utcnow


logger = logging.getLogger(__name__)

_DELIVERY_STATUSES = ("pending", "retrying")


async def outbound_queue_delivery_worker() -> None:
    client = WAHAClient()
    try:
        while True:
            delivered = await _deliver_due_outbound_messages(client)
            await asyncio.sleep(1 if delivered else 3)
    except asyncio.CancelledError:
        raise
    finally:
        await client.close()


async def scheduled_action_worker() -> None:
    """Release due owner-approved actions into the existing outbound queue."""
    try:
        while True:
            async with SessionLocal() as session:
                released = await ScheduledActionService(session).release_due(limit=25)
                if released:
                    await session.commit()
                    log_event(logger, logging.INFO, "scheduled_actions_released", count=released)
            await asyncio.sleep(1 if released else 3)
    except asyncio.CancelledError:
        raise


async def conversation_takeover_worker() -> None:
    try:
        while True:
            async with SessionLocal() as session:
                claimed = await ConversationTakeoverService(session).claim_due()
                if claimed:
                    await session.commit()
                    log_event(logger, logging.INFO, "conversation_takeovers_started", count=claimed)
            await asyncio.sleep(1 if claimed else 3)
    except asyncio.CancelledError:
        raise


async def conversation_open_loop_worker() -> None:
    """Keep unresolved questions/requests durable and projected into Memory context."""
    try:
        while True:
            async with SessionLocal() as session:
                result = await ConversationOpenLoopService(session).scan_once(limit=100)
                if result["processed"]:
                    await session.commit()
                    if result["created"] or result["repeated"] or result["resolved"]:
                        log_event(logger, logging.INFO, "conversation_open_loops_updated", **result)
            await asyncio.sleep(2 if result["processed"] else 5)
    except asyncio.CancelledError:
        raise


async def waha_monitor_worker() -> None:
    client = WAHAClient()
    previous_status: str | None = None
    try:
        while True:
            current_status = "unknown"
            details: dict[str, Any] = {}
            try:
                status_payload = await client.get_session_status()
                current_status = _extract_waha_status(status_payload)
                details["status_payload"] = status_payload
            except WahaClientError as exc:
                current_status = "error"
                details["error"] = str(exc)

            if current_status != "WORKING":
                reconnect_success = False
                reconnect_error: str | None = None
                try:
                    reconnect_payload = await client.start_session()
                    reconnect_success = True
                    details["reconnect_payload"] = reconnect_payload
                except WahaClientError as exc:
                    reconnect_error = str(exc)
                    details["reconnect_error"] = reconnect_error

                await _record_waha_outage(
                    previous_status=previous_status,
                    current_status=current_status,
                    reconnect_success=reconnect_success,
                    details=details,
                )
                log_event(
                    logger,
                    logging.WARNING,
                    "waha_monitor_reconnect",
                    previous_status=previous_status,
                    current_status=current_status,
                    reconnect_success=reconnect_success,
                    error=reconnect_error,
                )

            previous_status = current_status
            await asyncio.sleep(60)
    except asyncio.CancelledError:
        raise
    finally:
        await client.close()


async def _deliver_due_outbound_messages(client: WAHAClient) -> int:
    now = utcnow()
    async with SessionLocal() as session:
        stmt = (
            select(OutboundMessage)
            .where(
                or_(
                    OutboundMessage.status.in_(_DELIVERY_STATUSES),
                    OutboundMessage.status == "sending",
                )
            )
            .where(OutboundMessage.next_attempt_at <= now)
            .order_by(OutboundMessage.next_attempt_at, OutboundMessage.id)
            .limit(10)
            .with_for_update(skip_locked=True)
        )
        messages = (await session.execute(stmt)).scalars().all()
        due_messages: list[OutboundMessage] = []
        for message in messages:
            if message.status == "sending" and message.updated_at and message.updated_at > now - timedelta(minutes=5):
                continue
            message.status = "sending"
            message.updated_at = now
            due_messages.append(message)
        await session.commit()

        processed = 0
        for message in due_messages:
            processed += 1
            try:
                if message.media_url:
                    response = await client.send_media(
                        chat_id=message.chat_id,
                        media_url=message.media_url,
                        caption=message.media_caption or message.message_text,
                    )
                else:
                    response = await client.send_text(chat_id=message.chat_id, text=message.message_text)
            except WahaClientError as exc:
                await _mark_delivery_failed(session, message, str(exc))
            else:
                message.status = "sent"
                message.error_message = None
                message.updated_at = utcnow()
                await ScheduledActionService(session).reconcile_outbound_delivery(message)
                session.add(
                    AuditLog(
                        action="outbound_queue_sent",
                        entity_type="outbound_queue",
                        entity_id=str(message.id),
                        details_json={
                            "chat_id": message.chat_id,
                            "delivery_snapshot": _delivery_snapshot(message),
                            "waha_response": response,
                        },
                    )
                )
                await session.commit()
                log_event(logger, logging.INFO, "outbound_queue_sent", queue_id=message.id, chat_id=message.chat_id)
        return processed


def _delivery_snapshot(message: OutboundMessage) -> dict[str, str]:
    """Mirror the exact branch used by WAHA delivery when recording durable history."""
    if message.media_url:
        return {
            "text": message.media_caption or message.message_text,
            "message_type": message.media_type or "image",
        }
    return {
        "text": message.message_text,
        "message_type": "text",
    }


async def _mark_delivery_failed(session, message: OutboundMessage, error: str) -> None:
    next_retry_count = message.retry_count + 1
    message.retry_count = next_retry_count
    message.error_message = error[:2000]
    message.updated_at = utcnow()

    if next_retry_count > message.max_retries:
        message.status = "failed"
    else:
        message.status = "retrying"
        message.next_attempt_at = utcnow() + _retry_delay(next_retry_count)

    await ScheduledActionService(session).reconcile_outbound_delivery(message)
    session.add(
        AuditLog(
            action="outbound_queue_delivery_failed",
            entity_type="outbound_queue",
            entity_id=str(message.id),
            details_json={
                "chat_id": message.chat_id,
                "status": message.status,
                "retry_count": message.retry_count,
                "max_retries": message.max_retries,
                "error": message.error_message,
            },
        )
    )
    await session.commit()
    log_event(
        logger,
        logging.ERROR,
        "outbound_queue_delivery_failed",
        queue_id=message.id,
        chat_id=message.chat_id,
        status=message.status,
        retry_count=message.retry_count,
        error=error,
    )


async def _record_waha_outage(
    *,
    previous_status: str | None,
    current_status: str,
    reconnect_success: bool,
    details: dict[str, Any],
) -> None:
    async with SessionLocal() as session:
        outage = WahaOutage(
            previous_status=previous_status,
            current_status=current_status,
            reconnect_attempted=True,
            reconnect_success=reconnect_success,
            details_json=details,
        )
        session.add(outage)
        session.add(
            AuditLog(
                action="waha_outage_detected",
                entity_type="waha_outage",
                entity_id=None,
                details_json={
                    "previous_status": previous_status,
                    "current_status": current_status,
                    "reconnect_success": reconnect_success,
                },
            )
        )
        await session.commit()


def _extract_waha_status(payload: dict[str, Any]) -> str:
    for key in ("status", "state", "sessionStatus"):
        value = payload.get(key)
        if value:
            return str(value).upper()
    nested = payload.get("session")
    if isinstance(nested, dict):
        for key in ("status", "state", "sessionStatus"):
            value = nested.get(key)
            if value:
                return str(value).upper()
    return "unknown"


def _retry_delay(retry_count: int) -> timedelta:
    if retry_count <= 1:
        return timedelta(seconds=30)
    if retry_count == 2:
        return timedelta(minutes=2)
    return timedelta(minutes=10)

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta
import logging
from typing import Any

from sqlalchemy import or_, select

from app.db import SessionLocal
from app.models.schema import AuditLog, OutboundMessage, WahaOutage
from app.services.conversation_open_loop_service import ConversationOpenLoopService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.logging_service import log_event
from app.services.scheduled_action_service import ScheduledActionService
from app.services.view_once_media_service import ViewOnceMediaService
from app.services.waha_client import WAHAClient, WahaClientError
from app.utils.time import utcnow


logger = logging.getLogger(__name__)

_DELIVERY_STATUSES = ("pending", "retrying")
_VIEW_ONCE_RESEND_BLOCKED_ERROR = (
    "View-once media is no longer available for resend after its temporary WAHA file capability was scrubbed."
)
_VIEW_ONCE_CAPABILITY_EXPIRED_ERROR = (
    "View-once media delivery capability expired before delivery and was scrubbed."
)
_AUDIT_ENTITY_ID_MAX_CHARS = 120


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
            if await _expire_stale_view_once_capability(session, message):
                continue
            if await _block_scrubbed_view_once_resend(session, message):
                continue
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
                delivery_snapshot = _delivery_snapshot(message)
                audit_response = _waha_response_for_audit(message, response)
                message.status = "sent"
                message.error_message = None
                message.updated_at = utcnow()

                await _finalize_view_once_delivery_success(session, message, delivery_snapshot)
                await ScheduledActionService(session).reconcile_outbound_delivery(message)
                session.add(
                    AuditLog(
                        action="outbound_queue_sent",
                        entity_type="outbound_queue",
                        entity_id=str(message.id),
                        details_json={
                            "chat_id": message.chat_id,
                            "delivery_snapshot": delivery_snapshot,
                            "waha_response": audit_response,
                        },
                    )
                )
                await session.commit()
                log_event(logger, logging.INFO, "outbound_queue_sent", queue_id=message.id, chat_id=message.chat_id)
        return processed


async def _expire_stale_view_once_capability(session, message: OutboundMessage) -> bool:
    """Scrub a temporary view-once URL after its absolute delivery TTL.

    Retention is OFF, so a durable WAHA file capability must never remain eligible
    indefinitely merely because the delivery worker was paused or retries were
    delayed. Legacy view-once rows with no valid expiry are failed closed as stale.
    """
    source_id = _view_once_source_id(message)
    if not source_id or not message.media_url:
        return False

    expires_at = _view_once_capability_expires_at(message)
    if expires_at is not None and expires_at > utcnow():
        return False

    message.media_url = None
    message.status = "failed"
    message.error_message = _VIEW_ONCE_CAPABILITY_EXPIRED_ERROR
    message.updated_at = utcnow()
    _mark_view_once_non_resendable(message)
    await ViewOnceMediaService(session).mark_delivery_unavailable(source_id)
    session.add(
        AuditLog(
            action="view_once_delivery_capability_expired",
            entity_type="view_once_media",
            entity_id=_view_once_audit_entity_id(source_id),
            details_json={
                "outbound_queue_id": message.id,
                "reason": "absolute_delivery_ttl_elapsed",
            },
        )
    )
    await session.commit()
    log_event(
        logger,
        logging.WARNING,
        "view_once_delivery_capability_expired",
        queue_id=message.id,
        chat_id=message.chat_id,
    )
    return True


async def _block_scrubbed_view_once_resend(session, message: OutboundMessage) -> bool:
    """Fail closed when an operator resets a scrubbed view-once media row."""
    source_id = _view_once_source_id(message)
    if not source_id or message.media_url:
        return False

    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    if metadata.get("resendable") is not False and message.message_text.strip():
        return False

    message.status = "failed"
    message.error_message = _VIEW_ONCE_RESEND_BLOCKED_ERROR
    message.updated_at = utcnow()
    _mark_view_once_non_resendable(message)
    session.add(
        AuditLog(
            action="view_once_resend_blocked",
            entity_type="view_once_media",
            entity_id=_view_once_audit_entity_id(source_id),
            details_json={
                "outbound_queue_id": message.id,
                "reason": "temporary_media_capability_scrubbed",
            },
        )
    )
    await session.commit()
    log_event(
        logger,
        logging.WARNING,
        "view_once_resend_blocked",
        queue_id=message.id,
        chat_id=message.chat_id,
    )
    return True


async def _finalize_view_once_delivery_success(session, message: OutboundMessage, delivery_snapshot: dict[str, str]) -> None:
    view_once_source_id = _view_once_source_id(message)
    if not view_once_source_id:
        return

    await ViewOnceMediaService(session).mark_returned(view_once_source_id)
    message.media_url = None
    _mark_view_once_non_resendable(message)
    session.add(
        AuditLog(
            action="view_once_returned_to_owner",
            entity_type="view_once_media",
            entity_id=_view_once_audit_entity_id(view_once_source_id),
            details_json={
                "outbound_queue_id": message.id,
                "media_type": delivery_snapshot.get("message_type"),
            },
        )
    )


def _delivery_snapshot(message: OutboundMessage) -> dict[str, str]:
    if message.media_url:
        return {
            "text": message.media_caption or message.message_text,
            "message_type": message.media_type or "image",
        }
    return {"text": message.message_text, "message_type": "text"}


def _waha_response_for_audit(message: OutboundMessage, response: Any) -> Any:
    """Keep ordinary delivery auditing unchanged but redact view-once responses."""
    if not _view_once_source_id(message):
        return response

    snapshot: dict[str, Any] = {"redacted": True, "response_type": type(response).__name__}
    if not isinstance(response, dict):
        return snapshot

    for key in ("id", "messageId", "status", "source"):
        value = response.get(key)
        if isinstance(value, (str, int, float, bool)) and not isinstance(value, bytes):
            snapshot[key] = str(value)[:200]
    return snapshot


def _view_once_source_id(message: OutboundMessage) -> str | None:
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    if metadata.get("source") != "view_once_command":
        return None
    source_id = str(metadata.get("source_message_id") or "").strip()
    if not source_id:
        return None
    return source_id[:200]


def _view_once_audit_entity_id(source_id: str) -> str:
    """Map WAHA source IDs onto AuditLog.entity_id's VARCHAR(120) boundary."""
    return str(source_id).strip()[:_AUDIT_ENTITY_ID_MAX_CHARS]


def _view_once_capability_expires_at(message: OutboundMessage) -> datetime | None:
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    raw = str(metadata.get("capability_expires_at") or "").strip()
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if value.tzinfo is None:
        return None
    return value


def _mark_view_once_non_resendable(message: OutboundMessage) -> None:
    metadata = dict(message.formatting_json) if isinstance(message.formatting_json, dict) else {}
    if metadata.get("source") != "view_once_command" or not metadata.get("source_message_id"):
        return
    metadata["resendable"] = False
    message.formatting_json = metadata


async def _mark_delivery_failed(session, message: OutboundMessage, error: str) -> None:
    next_retry_count = message.retry_count + 1
    message.retry_count = next_retry_count
    message.error_message = error[:2000]
    now = utcnow()
    message.updated_at = now

    view_once_source_id = _view_once_source_id(message)
    capability_expires_at = _view_once_capability_expires_at(message) if view_once_source_id else None

    if next_retry_count > message.max_retries:
        message.status = "failed"
    elif view_once_source_id and capability_expires_at is not None and capability_expires_at <= now:
        message.status = "failed"
        message.error_message = _VIEW_ONCE_CAPABILITY_EXPIRED_ERROR
    else:
        message.status = "retrying"
        retry_at = now + _retry_delay(next_retry_count)
        if capability_expires_at is not None:
            retry_at = min(retry_at, capability_expires_at)
        message.next_attempt_at = retry_at

    if view_once_source_id and message.status == "failed":
        message.media_url = None
        _mark_view_once_non_resendable(message)
        await ViewOnceMediaService(session).mark_delivery_unavailable(view_once_source_id)
        session.add(
            AuditLog(
                action="view_once_delivery_terminal_failed",
                entity_type="view_once_media",
                entity_id=_view_once_audit_entity_id(view_once_source_id),
                details_json={
                    "outbound_queue_id": message.id,
                    "retry_count": message.retry_count,
                },
            )
        )

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

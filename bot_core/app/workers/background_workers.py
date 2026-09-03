from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from sqlalchemy import or_, select

from app.config import settings
from app.db import SessionLocal
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, OutboundMessage, WahaOutage
from app.services.conversation_open_loop_service import ConversationOpenLoopService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.logging_service import log_event
from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.services.outbound_media_dispatch_service import (
    MediaDispatchDecision,
    MediaDispatchPlan,
    OutboundMediaDispatchService,
)
from app.services.outbound_safety_limit_service import OutboundSafetyLimitService
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
        approval_ids: dict[int, int] = {}
        authority = OutboundAuthorizationService(session)
        safety = OutboundSafetyLimitService(session)
        for message in messages:
            if message.status == "sending":
                if message.updated_at and message.updated_at > now - timedelta(minutes=5):
                    continue
                await _mark_delivery_uncertain(
                    session,
                    message,
                    reason="delivery state uncertain after interrupted send; automatic replay blocked",
                    commit=False,
                )
                continue
            allowed, reason, approval_id = await _delivery_authorized(session, authority, message)
            if not allowed:
                await _mark_delivery_blocked(session, message, reason=reason)
                continue
            if not _is_owner_chat_id(message.chat_id):
                safety_decision = await safety.authorize(message, now=now)
                if not safety_decision.allowed:
                    await _mark_delivery_blocked(session, message, reason=safety_decision.reason)
                    continue
            if approval_id is not None:
                approval_ids[int(message.id)] = approval_id
            message.status = "sending"
            message.updated_at = now
            due_messages.append(message)
        await session.commit()

        processed = 0
        for message in due_messages:
            processed += 1
            dispatch: MediaDispatchDecision | None = None
            if message.media_url:
                # Runs only after the final authorization fence and safety limits have
                # already allowed this exact row. Dispatch can narrow behaviour or fail
                # closed; it can never authorize a row the fence rejected.
                dispatch = OutboundMediaDispatchService.plan(message)
                if not dispatch.allowed:
                    await _mark_delivery_blocked(session, message, reason=dispatch.reason)
                    await session.commit()
                    continue
            try:
                if dispatch is not None:
                    response = await _send_authorized_media(client, message, dispatch.plan)
                else:
                    response = await client.send_text(chat_id=message.chat_id, text=message.message_text)
            except WahaClientError as exc:
                await _mark_delivery_uncertain(
                    session,
                    message,
                    reason=f"WAHA delivery outcome uncertain; automatic replay blocked: {exc}",
                )
            else:
                approval_id = approval_ids.get(int(message.id))
                if approval_id is not None:
                    consumed = await OutboundAuthorizationService(session).consume_approval(approval_id)
                    if not consumed:
                        session.add(
                            AuditLog(
                                action="outbound_approval_consumption_invariant_failed",
                                entity_type="outbound_queue",
                                entity_id=str(message.id),
                                details_json={
                                    "chat_id": message.chat_id,
                                    "approval_id": approval_id,
                                },
                            )
                        )
                        log_event(
                            logger,
                            logging.ERROR,
                            "outbound_approval_consumption_invariant_failed",
                            queue_id=message.id,
                            approval_id=approval_id,
                        )
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
                            "approval_id": approval_id,
                        },
                    )
                )
                await session.commit()
                log_event(logger, logging.INFO, "outbound_queue_sent", queue_id=message.id, chat_id=message.chat_id)
        return processed


async def _send_authorized_media(client: WAHAClient, message: OutboundMessage, plan: MediaDispatchPlan) -> dict[str, Any]:
    """Issue exactly one typed WAHA media call for an already-authorized row.

    Each branch performs a single POST. The WAHA client marks media sends as
    non-retry-safe, so an ambiguous transport outcome propagates to the caller and is
    quarantined for reconciliation instead of being blindly resent.
    """
    if plan.operation == "send_media":
        return await client.send_media(
            chat_id=message.chat_id,
            media_url=message.media_url,
            caption=plan.caption,
        )
    if plan.operation == "send_image":
        return await client.send_image(
            message.chat_id,
            media_url=message.media_url,
            mimetype=plan.mimetype,
            caption=plan.caption,
            filename=plan.filename,
        )
    if plan.operation == "send_video":
        return await client.send_video(
            message.chat_id,
            media_url=message.media_url,
            mimetype=plan.mimetype,
            caption=plan.caption,
            filename=plan.filename,
        )
    if plan.operation == "send_voice":
        return await client.send_voice(
            message.chat_id,
            media_url=message.media_url,
            mimetype=plan.mimetype,
            filename=plan.filename,
        )
    if plan.operation == "send_file":
        return await client.send_file(
            message.chat_id,
            media_url=message.media_url,
            mimetype=plan.mimetype,
            caption=plan.caption,
            filename=plan.filename,
        )
    raise WahaClientError(f"unsupported outbound media operation: {plan.operation}")


async def _delivery_authorized(session, authority: OutboundAuthorizationService, message: OutboundMessage) -> tuple[bool, str, int | None]:
    """Apply the final outbound authorization fence against exact durable authority.

    Exact configured OWNER self-DM remains allowed. Router-generated external replies
    must pass OutboundAuthorizationService. A ScheduledAction may cross the fence only
    when its queue row proves the exact durable action/queue/target/content binding and
    the action is still enabled and queued. Missing metadata is never itself authority.
    """
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    delivery_policy = str(metadata.get("delivery_policy") or "").strip().lower()

    if _is_owner_chat_id(message.chat_id):
        # The owner destination is proven, but a row may additionally commit to its exact
        # payload. When that durable digest is present it must still match, so mutating a
        # private media locator/kind/caption/text after authority yields zero WAHA calls.
        stamped = str(metadata.get("authority_content_hash") or "").strip()
        if stamped and stamped != OutboundAuthorizationService.content_hash_for_message(message):
            return False, "owner queue row content mutated after authority", None
        return True, "exact configured owner chat", None

    if not delivery_policy:
        if await _is_exact_scheduled_action_binding(session, message, metadata):
            return True, "exact durable scheduled action binding", None
        return False, "external queue row missing explicit durable outbound authority", None

    if delivery_policy == "immediate":
        return False, "legacy external immediate router reply is not durably authorized", None
    if delivery_policy not in {"approval_required", "authorized_external"}:
        return False, f"unknown router delivery policy: {delivery_policy or 'missing'}", None

    _context, decision = await authority.authorize_queue_message(message)
    if not decision.allowed:
        return False, decision.reason, None
    return True, decision.reason, decision.approval_id


async def _is_exact_scheduled_action_binding(session, message: OutboundMessage, metadata: dict[str, Any]) -> bool:
    """Prove one ScheduledAction queue row without trusting queue metadata or content alone."""
    try:
        scheduled_action_id = int(metadata.get("scheduled_action_id"))
        outbound_queue_id = int(message.id)
    except (TypeError, ValueError):
        return False
    if scheduled_action_id <= 0 or outbound_queue_id <= 0 or session is None:
        return False

    row = (
        await session.execute(
            select(ScheduledAction)
            .where(ScheduledAction.id == scheduled_action_id)
            .where(ScheduledAction.outbound_queue_id == outbound_queue_id)
            .where(ScheduledAction.target_chat_id == message.chat_id)
            .where(ScheduledAction.action_type == "whatsapp.send_message")
            .where(ScheduledAction.status == "queued")
            .where(ScheduledAction.is_enabled.is_(True))
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        return False

    scheduled_text = (row.payload_json or {}).get("text")
    return isinstance(scheduled_text, str) and bool(scheduled_text) and message.message_text == scheduled_text


def _is_owner_chat_id(chat_id: str) -> bool:
    wanted = (chat_id or "").strip().lower()
    if not wanted:
        return False
    owner_ids = {
        item.strip().lower()
        for item in str(settings.owner_whatsapp_ids or "").replace(";", ",").split(",")
        if item.strip()
    }
    return wanted in owner_ids


async def _mark_delivery_blocked(session, message: OutboundMessage, *, reason: str) -> None:
    message.status = "deferred"
    message.error_message = reason[:2000]
    message.updated_at = utcnow()
    await ScheduledActionService(session).reconcile_outbound_delivery(message)
    session.add(
        AuditLog(
            action="outbound_queue_authorization_blocked",
            entity_type="outbound_queue",
            entity_id=str(message.id),
            details_json={
                "chat_id": message.chat_id,
                "status": message.status,
                "reason": message.error_message,
                "delivery_policy": (
                    message.formatting_json.get("delivery_policy")
                    if isinstance(message.formatting_json, dict)
                    else None
                ),
            },
        )
    )
    log_event(
        logger,
        logging.WARNING,
        "outbound_queue_authorization_blocked",
        queue_id=message.id,
        chat_id=message.chat_id,
        reason=reason,
    )


async def _mark_delivery_uncertain(
    session,
    message: OutboundMessage,
    *,
    reason: str,
    commit: bool = True,
) -> None:
    """Quarantine a row whose external send outcome cannot be proven.

    Replaying an uncertain row risks a duplicate real-world message. PostgreSQL keeps
    the row and evidence for OWNER reconciliation; no retry is scheduled automatically.
    """
    message.status = "deferred"
    message.error_message = reason[:2000]
    message.updated_at = utcnow()
    await ScheduledActionService(session).reconcile_outbound_delivery(message)
    session.add(
        AuditLog(
            action="outbound_queue_delivery_uncertain",
            entity_type="outbound_queue",
            entity_id=str(message.id),
            details_json={
                "chat_id": message.chat_id,
                "status": message.status,
                "reason": message.error_message,
                "retry_count": message.retry_count,
                "automatic_replay": False,
            },
        )
    )
    if commit:
        await session.commit()
    log_event(
        logger,
        logging.WARNING,
        "outbound_queue_delivery_uncertain",
        queue_id=message.id,
        chat_id=message.chat_id,
        automatic_replay=False,
    )


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
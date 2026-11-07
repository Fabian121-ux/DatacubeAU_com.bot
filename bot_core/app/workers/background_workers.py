from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any

from sqlalchemy import or_, select, text

from app.config import settings
from app.db import SessionLocal
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, OutboundMessage, WahaOutage
from app.services.conversation_open_loop_service import ConversationOpenLoopService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.logging_service import log_event
from app.services.contact_messaging_consent_service import ContactMessagingConsentService
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
            allowed, reason, _approval_id, _authority_type, _policy_id = await _delivery_authorized(session, authority, message)
            if not allowed:
                await _mark_delivery_blocked(session, message, reason=reason)
                continue
            if not _is_owner_chat_id(message.chat_id):
                safety_decision = await safety.authorize(message, now=now)
                if not safety_decision.allowed:
                    await _mark_delivery_blocked(session, message, reason=safety_decision.reason)
                    continue
            message.status = "sending"
            message.updated_at = now
            due_messages.append(message)
        await session.commit()

        processed = 0
        for message in due_messages:
            processed += 1
            # The initial batch check prevents unauthorized rows from being claimed.
            # Re-lock and refresh each row after that batch commit so a payload, approval,
            # policy, or scheduled-action mutation between claim and dispatch cannot use
            # the stale in-memory object to reach WAHA.
            await session.refresh(message, with_for_update=True)
            if message.status != "sending":
                await session.rollback()
                continue
            final_allowed, final_reason, final_approval_id, final_authority_type, final_policy_id = await _delivery_authorized(
                session,
                OutboundAuthorizationService(session),
                message,
                lock_chat_mapping=True,
            )
            if not final_allowed:
                await _mark_delivery_blocked(
                    session,
                    message,
                    reason=f"final outbound authority recheck failed: {final_reason}",
                )
                await session.commit()
                continue
            if (
                final_authority_type == "contact_policy" and final_policy_id is None
            ) or (
                final_authority_type == "owner_approval" and final_approval_id is None
            ):
                await _mark_delivery_blocked(
                    session,
                    message,
                    reason="final outbound authority is missing its exact policy/approval ID",
                )
                await session.commit()
                continue

            # This is the final external-contact consent fence, after the queue batch has
            # been committed as "sending". The consent service materializes an UNKNOWN
            # row if absent, then SELECTs it FOR UPDATE. Keep this transaction open through
            # the single WAHA attempt so grant/revoke/opt-out serialize on the same key.
            # OWNER self-DM remains on its existing exact-recipient + payload binding.
            if not _is_owner_chat_id(message.chat_id):
                consent = await ContactMessagingConsentService(session).authorize_outbound_queue_message(
                    message,
                )
                if not consent.allowed:
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason=f"contact consent denied: {consent.reason}",
                    )
                    await session.commit()
                    continue

            # Revalidate after the final authority, policy, Contact, and consent locks.
            # authorize() acquires the global transaction-scoped reservation lock, which
            # remains held through the single transport attempt and durable outcome.
            # This closes the gap where a row waits >1 minute at a final fence and its
            # timestamp-based reservation would otherwise age out before dispatch.
            if not _is_owner_chat_id(message.chat_id):
                final_safety = await OutboundSafetyLimitService(session).authorize(
                    message,
                    now=utcnow(),
                    contact_id=consent.contact_id,
                )
                if not final_safety.allowed:
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason=f"final outbound safety recheck failed: {final_safety.reason}",
                    )
                    await session.commit()
                    continue

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
            # A STOP receipt is committed before ingress waits on the exact-chat lock.
            # This is the final pre-transport veto: a claim committed before this read
            # blocks the send. Once this read completes, the single transport attempt is
            # considered in-flight and cannot be reliably cancelled after network entry.
            if not _is_owner_chat_id(message.chat_id):
                await ContactMessagingConsentService.lock_opt_out_dispatch_boundary(
                    session, message.chat_id
                )
                pending_opt_out = await ContactMessagingConsentService(
                    session
                ).has_pending_opt_out_intent_for_contact(consent.contact_id)
                if pending_opt_out:
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason="pending inbound opt-out intent; external delivery denied",
                    )
                    await session.commit()
                    continue

                # Quiet hours are a delivery restriction, not an authority source.
                # Apply the same final check to exact approvals and ScheduledActions;
                # keep its advisory/row locks through the one transport attempt.
                delivery_window = await OutboundAuthorizationService(
                    session
                ).check_contact_delivery_window(
                    contact_id=consent.contact_id,
                    exact_chat_id=message.chat_id,
                )
                if not delivery_window.allowed:
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason=f"final contact delivery window denied: {delivery_window.reason}",
                    )
                    await session.commit()
                    continue

                # Revalidate the original authority after every potentially blocking
                # final fence. A contact-policy row can expire while consent, safety,
                # or STOP locks are being acquired; absence of an active policy is not
                # authority for a row whose only authority was that policy. Exact
                # OWNER approvals and locked ScheduledActions remain independently
                # valid and are re-proved by this same authoritative helper.
                rechecked_allowed, rechecked_reason, rechecked_approval_id, rechecked_authority_type, rechecked_policy_id = await _delivery_authorized(
                    session,
                    OutboundAuthorizationService(session),
                    message,
                    lock_chat_mapping=True,
                )
                authority_changed = rechecked_authority_type != final_authority_type
                if final_authority_type == "owner_approval":
                    authority_changed = authority_changed or rechecked_approval_id != final_approval_id
                elif final_authority_type == "contact_policy":
                    authority_changed = authority_changed or rechecked_policy_id != final_policy_id
                if not rechecked_allowed or authority_changed:
                    reason = (
                        f"final outbound authority recheck failed: {rechecked_reason}"
                        if not rechecked_allowed
                        else "final outbound authority source or exact policy/approval ID changed before dispatch"
                    )
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason=reason,
                    )
                    await session.commit()
                    continue
                final_approval_id = rechecked_approval_id

            # A queued OWNER view-once return must still reference an active, exact source.
            # Lock that authoritative row before reserving the one-use approval and keep
            # the lock through the single WAHA attempt so OWNER deletion cannot race send.
            source_available, source_reason = await _lock_owner_view_once_source(
                session, message
            )
            if not source_available:
                await _mark_delivery_blocked(
                    session, message, reason=source_reason
                )
                await session.commit()
                continue

            # Reserve an exact one-use OWNER approval only after recipient, content,
            # STOP, safety, delivery-window, and final authority checks. Reservation is
            # not proof of delivery; an approval remains consumed if a later final
            # consent check denies the attempt.
            approval_id = final_approval_id
            if approval_id is not None:
                consumed = await OutboundAuthorizationService(session).consume_approval(
                    approval_id,
                    message=message,
                )
                if not consumed:
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason="final exact one-use OWNER approval reservation failed: approval expired, was consumed, or its queue binding changed",
                    )
                    await session.commit()
                    continue

            # This is the last time-bounded external-contact authorization check.
            # It deliberately follows the final delivery-window/authority checks and
            # the potentially blocking one-use approval reservation. No further
            # authorization query may run before the single transport attempt.
            if not _is_owner_chat_id(message.chat_id):
                final_consent = await ContactMessagingConsentService(
                    session
                ).revalidate_locked_outbound_queue_message_consent(
                    consent.contact_id,
                    message.chat_id,
                )
                if not final_consent.allowed:
                    if approval_id is not None:
                        session.add(
                            AuditLog(
                                action="outbound_approval_consumed_dispatch_blocked",
                                entity_type="outbound_queue",
                                entity_id=str(message.id),
                                details_json={
                                    "chat_id": message.chat_id,
                                    "approval_id": approval_id,
                                    "content_sha256": OutboundAuthorizationService.content_hash_for_message(message),
                                    "reason": final_consent.reason,
                                    "delivery_attempt_reserved": False,
                                },
                            )
                        )
                    await _mark_delivery_blocked(
                        session,
                        message,
                        reason=f"final contact consent denied: {final_consent.reason}",
                    )
                    await session.commit()
                    continue

            if approval_id is not None:
                session.add(
                    AuditLog(
                        action="outbound_approval_consumed_for_dispatch",
                        entity_type="outbound_queue",
                        entity_id=str(message.id),
                        details_json={
                            "chat_id": message.chat_id,
                            "approval_id": approval_id,
                            "content_sha256": OutboundAuthorizationService.content_hash_for_message(message),
                            "delivery_attempt_reserved": True,
                        },
                    )
                )

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
                await _mark_owner_view_once_returned(session, message)
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
                            "authority_type": final_authority_type,
                            "policy_id": final_policy_id,
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



async def _lock_owner_view_once_source(session, message: OutboundMessage) -> tuple[bool, str]:
    """Hold the exact view-once source row through the one OWNER return attempt."""
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    if metadata.get("source") != "owner_view_once":
        return True, ""
    source_message_id = metadata.get("source_message_id")
    if not isinstance(source_message_id, str) or not source_message_id.strip():
        return False, "owner view-once return missing exact source message id"
    source_chat_id = metadata.get("source_chat_id")
    if not isinstance(source_chat_id, str) or not source_chat_id.strip():
        return False, "owner view-once return missing exact source chat id"
    command_message_id = metadata.get("command_message_id")
    if not isinstance(command_message_id, str) or not command_message_id.strip():
        return False, "owner view-once return missing exact command message id"

    result = await session.execute(
        text(
            """
            SELECT source_message_id, source_chat_id FROM view_once_media_metadata
            WHERE source_message_id = :source_message_id AND deleted_at IS NULL
            FOR UPDATE
            """
        ),
        {"source_message_id": source_message_id},
    )
    source = result.mappings().one_or_none()
    if source is None:
        return False, "view-once source was deleted or is no longer active before dispatch"
    if str(source["source_chat_id"] or "") != source_chat_id:
        return False, "view-once source chat does not match authoritative metadata before dispatch"
    return True, ""


async def _mark_owner_view_once_returned(session, message: OutboundMessage) -> None:
    """Record the return only after WAHA confirms the single transport attempt."""
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    if metadata.get("source") != "owner_view_once":
        return
    source_message_id = metadata.get("source_message_id")
    if not isinstance(source_message_id, str) or not source_message_id.strip():
        log_event(logger, logging.ERROR, "view_once_return_delivery_invariant_failed", queue_id=message.id)
        return
    result = await session.execute(
        text(
            """
            UPDATE view_once_media_metadata
            SET returned_to_owner_at = now(), last_observed_at = now()
            WHERE source_message_id = :source_message_id AND deleted_at IS NULL
            """
        ),
        {"source_message_id": source_message_id},
    )
    if result.rowcount != 1:
        session.add(
            AuditLog(
                action="view_once_return_delivery_invariant_failed",
                entity_type="outbound_queue",
                entity_id=str(message.id),
                details_json={"source_message_id": source_message_id},
            )
        )
        log_event(
            logger,
            logging.ERROR,
            "view_once_return_delivery_invariant_failed",
            queue_id=message.id,
            source_message_id=source_message_id,
        )
        return
    session.add(
        AuditLog(
            action="view_once_returned_to_owner",
            entity_type="view_once_media_metadata",
            entity_id=source_message_id,
            details_json={
                "outbound_queue_id": message.id,
                "source_message_id": source_message_id,
            },
        )
    )


async def _delivery_authorized(
    session,
    authority: OutboundAuthorizationService,
    message: OutboundMessage,
    *,
    lock_chat_mapping: bool = False,
) -> tuple[bool, str, int | None, str | None, int | None]:
    """Apply the final outbound authorization fence against exact durable authority.

    Exact configured OWNER self-DM remains allowed. Router-generated external replies
    must pass OutboundAuthorizationService. A ScheduledAction may cross the fence only
    when its queue row proves the exact durable action/queue/target/content binding and
    the action is still enabled and queued. Missing metadata is never itself authority.
    """
    metadata = message.formatting_json if isinstance(message.formatting_json, dict) else {}
    if "delivery_outcome_uncertain" in metadata:
        return False, "queue row has an uncertain prior transport outcome; replay denied", None, None, None
    delivery_policy = str(metadata.get("delivery_policy") or "").strip().lower()

    if _is_owner_chat_id(message.chat_id):
        # The exact configured OWNER destination proves *where* this row may go. It says
        # nothing about *what* it carries, so the payload binding is still required.
        # Anything able to write to an owner-destined row between creation and delivery
        # would otherwise gain full send authority over Fabian's own inbox.
        #
        # This is fail-closed by design: an unstamped executable owner row is refused
        # rather than delivered, so a producer that forgets to stamp fails safe instead
        # of silently inheriting unbounded authority from the destination alone.
        if not OutboundAuthorizationService.owner_payload_matches(message):
            return False, "owner queue row payload is not bound to its authorized content", None, None, None
        return True, "exact configured owner chat with bound payload", None, "owner_chat", None

    if not delivery_policy:
        if await _is_exact_scheduled_action_binding(session, message, metadata):
            return True, "exact durable scheduled action binding", None, "scheduled_action", None
        return False, "external queue row missing explicit durable outbound authority", None, None, None

    if delivery_policy == "immediate":
        return False, "legacy external immediate router reply is not durably authorized", None, None, None
    if delivery_policy not in {"approval_required", "authorized_external"}:
        return False, f"unknown router delivery policy: {delivery_policy or 'missing'}", None, None, None

    if lock_chat_mapping:
        _context, decision = await authority.authorize_queue_message(
            message,
            lock_chat_mapping=True,
        )
    else:
        _context, decision = await authority.authorize_queue_message(message)
    if not decision.allowed:
        return False, decision.reason, None, decision.authority_type, decision.policy_id
    return True, decision.reason, decision.approval_id, decision.authority_type, decision.policy_id


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
            # The caller already owns the outbound_queue row lock. Lock the exact
            # action second and refresh any identity-map copy so OWNER state changes
            # serialize with this final reservation through transport + outcome commit.
            .with_for_update()
            .execution_options(populate_existing=True)
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
    the row and evidence for OWNER reconciliation; a durable one-way marker blocks
    both OWNER requeue and the final worker fence from replaying this exact row.
    """
    # This marker survives restart and is deliberately never cleared by requeue.
    metadata = dict(message.formatting_json) if isinstance(message.formatting_json, dict) else {}
    metadata["delivery_outcome_uncertain"] = True
    message.formatting_json = metadata
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
                "delivery_outcome_uncertain": True,
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
        delivery_outcome_uncertain=True,
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
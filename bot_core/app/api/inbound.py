from __future__ import annotations

import hmac
import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Request, status

from app.config import settings
from app.core.message_normalizer import MessageNormalizer
from app.core.router import InboundRouter
from app.db import SessionLocal
from app.models.schema import AuditLog
from app.services.admin_management_service import AdminManagementService
from app.services.command_control_service import CommandControlService
from app.services.conversation_handback_service import ConversationHandbackService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.inbound_idempotency_service import InboundIdempotencyService, InboundReceipt
from app.services.logging_service import log_event
from app.services.natural_action_planner_service import NaturalActionPlannerService
from app.services.outbound_origin_service import OutboundOriginService


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/webhooks/waha", status_code=status.HTTP_202_ACCEPTED)
async def waha_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
) -> dict[str, Any]:
    # Privileged `fromMe` commands must never trust caller-controlled payload identity
    # alone. Reuse the configured WAHA API key as a shared webhook header secret.
    # Non-production environments may omit the key for local test compatibility.
    if not _webhook_authenticated(request):
        log_event(logger, logging.WARNING, "webhook_ignored", reason="unauthorized_webhook")
        return {"status": "ignored", "reason": "unauthorized_webhook"}

    # Parse body defensively — never return 422 to WAHA or it retries aggressively.
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

    # Status posts, channels/newsletters, and broadcast lists are not conversations.
    # Reject them before the idempotency claim and before any routing side effect so
    # they can never become a reply candidate.
    if _is_non_conversational_chat(_resolve_chat_id(payload)):
        log_event(
            logger,
            logging.INFO,
            "webhook_ignored",
            request_id=request_id,
            event_name=event_name or "message",
            message_id=message_id,
            reason="non_conversational_chat",
        )
        return {
            "status": "ignored",
            "reason": "non_conversational_chat",
            "event_name": event_name or "message",
        }

    # Bind privileged owner-authored events to the configured WAHA session. A valid
    # shared secret from another/old session is not enough to execute owner commands.
    if _is_from_me(payload) and not _session_matches_config(event, payload):
        log_event(
            logger,
            logging.WARNING,
            "webhook_ignored",
            request_id=request_id,
            event_name=event_name or "message",
            message_id=message_id,
            reason="unexpected_session",
        )
        return {"status": "ignored", "reason": "unexpected_session", "event_name": event_name or "message"}

    # Claim every message event before *any* command/action side effect. WAHA may
    # deliver the same message as both `message` and `message.any`, and webhook
    # retries must not execute owner commands twice.
    idempotency_key = _build_idempotency_key(event, payload)
    if idempotency_key:
        receipt = InboundReceipt(
            event_key=idempotency_key,
            session_name=_resolve_session_name(event, payload),
            chat_id=_resolve_chat_id(payload),
            message_id=message_id,
        )
        async with SessionLocal() as db:
            claimed = await InboundIdempotencyService(db).claim(receipt)
        if not claimed:
            log_event(
                logger,
                logging.INFO,
                "webhook_duplicate_ignored",
                request_id=request_id,
                event_name=event_name or "message",
                message_id=message_id,
                idempotency_key=idempotency_key,
            )
            return {
                "status": "duplicate",
                "request_id": request_id,
                "event_name": event_name or "message",
                "message_id": message_id,
            }

    if _is_from_me(payload):
        chat_id = _resolve_chat_id(payload)
        handback_generated = False
        command_consumed = False
        command_name: str | None = None
        command_error: str | None = None
        command_outbound_queue_id: int | None = None
        natural_action_queued = False
        natural_action_error: str | None = None
        takeover_cancelled = False
        try:
            if chat_id and not _is_group_chat(chat_id):
                async with SessionLocal() as db:
                    # With `message.any` enabled, WAHA echoes API-sent Zina output as
                    # `fromMe`. Prefer the causal `source` already present on the
                    # authenticated webhook; the service only falls back to a WAHA
                    # message lookup when this event did not include source evidence.
                    if await OutboundOriginService(db).is_zina_originated(
                        chat_id=chat_id,
                        transport_message_id=message_id,
                        transport_source=_resolve_transport_source(payload),
                    ):
                        if idempotency_key:
                            await InboundIdempotencyService(db).mark_completed(idempotency_key, commit=False)
                        await db.commit()
                        log_event(
                            logger,
                            logging.INFO,
                            "webhook_ignored",
                            request_id=request_id,
                            event_name=event_name or "message.any",
                            message_id=message_id,
                            chat_id=chat_id,
                            reason="zina_outbound_echo",
                        )
                        return {
                            "status": "ignored",
                            "reason": "zina_outbound_echo",
                            "event_name": event_name or "message.any",
                            "message_id": message_id,
                        }

                    normalized = MessageNormalizer().normalize(event)
                    control_only = CommandControlService.is_non_takeover_control(normalized.message_text)

                    # `.push` is a control action, not a human conversational reply.
                    # Do not resume Fabian or cancel a deferred Zina response merely
                    # because he archived a quoted message from this peer DM.
                    if not control_only:
                        takeover_cancelled = await ConversationTakeoverService(db).record_owner_reply(chat_id=chat_id)
                        handback = await ConversationHandbackService(db).generate_if_needed(chat_id=chat_id)
                        handback_generated = handback is not None

                    command_result = await CommandControlService(db).handle_from_me(
                        normalized,
                        transport_message_id=message_id,
                        request_id=request_id,
                    )
                    if command_result is not None and command_result.consumed:
                        command_consumed = True
                        command_name = command_result.command
                        command_error = command_result.error
                        command_outbound_queue_id = command_result.outbound_queue_id
                    else:
                        natural_action = await _plan_owner_natural_action(
                            db,
                            event=event,
                            message_id=message_id,
                            request_id=request_id,
                        )
                        natural_action_queued = bool(natural_action and natural_action.get("scheduled_action"))
                        natural_action_error = natural_action.get("error") if natural_action else None

                    # Side effects and receipt completion must commit atomically. If
                    # this transaction fails, release_failed can safely permit retry.
                    if idempotency_key:
                        await InboundIdempotencyService(db).mark_completed(idempotency_key, commit=False)
                    await db.commit()
                log_event(
                    logger,
                    logging.INFO,
                    "conversation_owner_activity",
                    request_id=request_id,
                    chat_id=chat_id,
                    takeover_cancelled=takeover_cancelled,
                    handback_generated=handback_generated,
                    command_consumed=command_consumed,
                    command_name=command_name,
                    command_error=command_error,
                    command_outbound_queue_id=command_outbound_queue_id,
                    natural_action_queued=natural_action_queued,
                    natural_action_error=natural_action_error,
                )
            elif idempotency_key:
                # Group/unknown `fromMe` events have no owner command side effects,
                # but still complete their durable receipt.
                async with SessionLocal() as db:
                    await InboundIdempotencyService(db).mark_completed(idempotency_key)
        except Exception:  # noqa: BLE001
            if idempotency_key:
                async with SessionLocal() as db:
                    await InboundIdempotencyService(db).release_failed(idempotency_key)
            raise

        accepted = command_consumed or natural_action_queued
        reason = "owner_command_control" if command_consumed else "owner_natural_action" if natural_action_queued else "from_me"
        log_event(
            logger,
            logging.INFO,
            "webhook_ignored" if not accepted else "webhook_owner_action_accepted",
            request_id=request_id,
            event_name=event_name or "message",
            message_id=message_id,
            reason=reason,
            handback_generated=handback_generated,
            command_consumed=command_consumed,
            command_name=command_name,
            command_error=command_error,
            command_outbound_queue_id=command_outbound_queue_id,
            natural_action_queued=natural_action_queued,
            natural_action_error=natural_action_error,
        )
        return {
            "status": "accepted" if accepted else "ignored",
            "reason": reason,
            "event_name": event_name or "message",
            "handback_generated": handback_generated,
            "command_consumed": command_consumed,
            "command": command_name,
            "command_error": command_error,
            "command_outbound_queue_id": command_outbound_queue_id,
            "natural_action_queued": natural_action_queued,
            "natural_action_error": natural_action_error,
        }

    background_tasks.add_task(_process_event_async, event, request_id, idempotency_key)
    log_event(
        logger,
        logging.INFO,
        "webhook_queued",
        request_id=request_id,
        event_name=event_name or "message",
        message_id=message_id,
        idempotency_key=idempotency_key,
    )
    return {
        "status": "accepted",
        "request_id": request_id,
        "event_name": event_name or "message",
        "message_id": message_id,
    }


async def _plan_owner_natural_action(
    db,
    *,
    event: dict[str, Any],
    message_id: str | None,
    request_id: str,
) -> dict[str, Any] | None:
    """Plan a narrow owner-authored natural action without routing arbitrary fromMe text."""
    normalized = MessageNormalizer().normalize(event)
    if normalized.chat_type.value != "dm" or not normalized.message_text.strip():
        return None

    # Parsing is side-effect free and deliberately narrow. Non-actions stay normal owner activity.
    try:
        plan = NaturalActionPlannerService.parse(normalized.message_text)
    except ValueError as exc:
        return {"error": str(exc)}
    if plan is None:
        return None

    admin = await AdminManagementService(db).resolve_admin_message(normalized)
    if not admin:
        db.add(
            AuditLog(
                action="owner_natural_action_denied",
                entity_type="scheduled_actions",
                details_json={"request_id": request_id, "transport_message_id": message_id},
            )
        )
        return {"error": "owner authorization failed"}

    try:
        result = await NaturalActionPlannerService(db).create_from_instruction(
            normalized.message_text,
            actor_permission=admin.permission_level,
            source_message_id=None,
            requested_by_contact_id=None,
            idempotency_key=_owner_action_idempotency_key(event, normalized.payload),
        )
    except ValueError as exc:
        resolution = getattr(exc, "resolution", None)
        db.add(
            AuditLog(
                action="owner_natural_action_rejected",
                entity_type="scheduled_actions",
                details_json={
                    "request_id": request_id,
                    "transport_message_id": message_id,
                    "reason": str(exc),
                    "resolution_status": resolution.get("status") if isinstance(resolution, dict) else None,
                    "permission": admin.permission_level,
                },
            )
        )
        return {"error": str(exc)}

    db.add(
        AuditLog(
            action="owner_natural_action_accepted",
            entity_type="scheduled_actions",
            entity_id=str(result["scheduled_action"]["id"]) if result else None,
            details_json={
                "request_id": request_id,
                "transport_message_id": message_id,
                "permission": admin.permission_level,
            },
        )
    )
    return result


async def _process_event_async(
    event: dict[str, Any],
    request_id: str,
    idempotency_key: str | None = None,
) -> None:
    async with SessionLocal() as db:
        inbound_router = InboundRouter(db)
        result: dict[str, Any] | None = None
        error_text: str | None = None
        takeover_scheduled = False
        try:
            result = await inbound_router.process_event(event)
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            error_text = str(exc)
            if idempotency_key:
                await InboundIdempotencyService(db).release_failed(idempotency_key)
            log_event(logger, logging.ERROR, "webhook_processing_failed", request_id=request_id, error=error_text)
            logger.exception("WAHA inbound processing failed")
        else:
            payload = _resolve_payload(event)
            chat_id = _resolve_chat_id(payload)
            if chat_id and not _is_group_chat(chat_id):
                reply_deferred = bool(result.get("reply_deferred"))
                takeover_scheduled = await ConversationTakeoverService(db).schedule_if_eligible(
                    chat_id=chat_id,
                    chat_type=str(result.get("chat_type") or ""),
                    message_id=_resolve_message_id(payload),
                    router_replied=bool(result.get("outbound_message_id") or result.get("outbound_queue_id")),
                    reply_deferred=reply_deferred,
                    outbound_queue_id=(int(result["outbound_queue_id"]) if result.get("outbound_queue_id") else None),
                )
            if idempotency_key:
                await InboundIdempotencyService(db).mark_completed(idempotency_key)
            else:
                await db.commit()
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
            idempotency_key=idempotency_key,
            takeover_scheduled=takeover_scheduled,
            reply_deferred=result.get("reply_deferred") if result else None,
        )


def _webhook_authenticated(request: Request) -> bool:
    configured = (settings.waha_api_key or "").strip()
    if not configured:
        return settings.environment.strip().lower() != "production"
    supplied = (
        request.headers.get("x-api-key")
        or request.headers.get("x-waha-api-key")
        or ""
    ).strip()
    if not supplied:
        authorization = (request.headers.get("authorization") or "").strip()
        if authorization.lower().startswith("bearer "):
            supplied = authorization[7:].strip()
    return bool(supplied) and hmac.compare_digest(supplied, configured)


def _session_matches_config(event: dict[str, Any], payload: dict[str, Any]) -> bool:
    actual = (_resolve_session_name(event, payload) or "").strip()
    expected = (settings.waha_session_name or "").strip()
    return bool(actual and expected and hmac.compare_digest(actual, expected))


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


def _resolve_chat_id(payload: dict[str, Any]) -> str | None:
    nested_chat = payload.get("chat") if isinstance(payload.get("chat"), dict) else {}
    raw_chat_id = payload.get("chatId") or nested_chat.get("id") or payload.get("from")
    if raw_chat_id is None:
        return None
    text = str(raw_chat_id).strip()
    return text or None


def _resolve_transport_source(payload: dict[str, Any]) -> str | None:
    nested_data = payload.get("_data") if isinstance(payload.get("_data"), dict) else {}
    raw_source = payload.get("source") or nested_data.get("source")
    if raw_source is None:
        return None
    text = str(raw_source).strip().lower()
    return text or None


def _resolve_session_name(event: dict[str, Any], payload: dict[str, Any]) -> str | None:
    raw_session = event.get("session") or payload.get("session")
    if isinstance(raw_session, dict):
        raw_session = raw_session.get("name") or raw_session.get("id")
    if raw_session is None:
        return None
    text = str(raw_session).strip()
    return text or None


def _build_idempotency_key(event: dict[str, Any], payload: dict[str, Any]) -> str | None:
    """Build a stable key shared by `message` and `message.any` deliveries."""
    message_id = _resolve_message_id(payload)
    if not message_id:
        return None
    session_name = _resolve_session_name(event, payload) or "default"
    chat_id = _resolve_chat_id(payload) or "unknown-chat"
    return f"{session_name}:{chat_id}:{message_id}"


def _owner_action_idempotency_key(event: dict[str, Any], payload: dict[str, Any]) -> str | None:
    base = _build_idempotency_key(event, payload)
    return f"owner-natural-action:{base}" if base else None


def _is_non_conversational_chat(chat_id: str | None) -> bool:
    """Identify WhatsApp surfaces that are broadcasts, not real conversations.

    Status updates, channels/newsletters, and broadcast lists arrive as ordinary
    `message` events, and the normalizer classifies any non-`@g.us` chat as a DM. Left
    unguarded they would enter reply planning and could produce an outbound reply to a
    status post. These surfaces are never a legitimate reply target for Zina.
    """
    normalized = str(chat_id or "").strip().lower()
    if not normalized:
        return False
    return (
        normalized == "status@broadcast"
        or normalized.endswith("@broadcast")
        or normalized.endswith("@newsletter")
    )


def _is_from_me(payload: dict[str, Any]) -> bool:
    raw_value = payload.get("fromMe")
    if isinstance(raw_value, bool):
        return raw_value
    if isinstance(raw_value, str):
        return raw_value.strip().lower() in {"1", "true", "yes"}
    return False


def _is_group_chat(chat_id: str) -> bool:
    return chat_id.endswith("@g.us")

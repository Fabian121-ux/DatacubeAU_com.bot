from __future__ import annotations

import logging
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.router import InboundRouter
from app.db import SessionLocal, get_db_session
from app.services.command_control_service import CommandControlService
from app.services.conversation_handback_service import ConversationHandbackService
from app.services.conversation_takeover_service import ConversationTakeoverService
from app.services.inbound_idempotency_service import InboundIdempotencyService
from app.services.logging_service import log_event
from app.services.message_normalizer import MessageNormalizer
from app.services.natural_action_planner_service import NaturalActionPlannerService
from app.services.outbound_origin_service import OutboundOriginService
from app.services.admin_management_service import AdminManagementService


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/webhook/waha")
async def waha_webhook(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    request_id = str(uuid.uuid4())
    event = await request.json()
    event_name = str(event.get("event") or "")
    payload = event.get("payload") if isinstance(event.get("payload"), dict) else {}
    message_id = str(payload.get("id") or "") or None

    _authenticate_waha_webhook(request)
    _validate_waha_session(event)

    idempotency_key = InboundIdempotencyService.build_event_key(event)
    if idempotency_key:
        async with SessionLocal() as db:
            claimed = await InboundIdempotencyService(db).claim(idempotency_key)
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
                    # `message.any` includes causal transport origin: WAHA marks API-
                    # created messages as `source=api` and WhatsApp-authored messages
                    # as `source=app`. Pass that evidence into the origin guard before
                    # applying any owner activity, while retaining exact completed-ID
                    # correlation for engines/events that omit source.
                    if await OutboundOriginService(db).is_zina_originated(
                        chat_id=chat_id,
                        transport_message_id=message_id,
                        transport_source=str(payload.get("source") or ""),
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

            return {
                "status": "ignored",
                "reason": "from_me",
                "event_name": event_name or "message",
                "message_id": message_id,
                "takeover_cancelled": takeover_cancelled,
                "handback_generated": handback_generated,
                "command_consumed": command_consumed,
                "command_name": command_name,
                "command_error": command_error,
                "command_outbound_queue_id": command_outbound_queue_id,
                "natural_action_queued": natural_action_queued,
                "natural_action_error": natural_action_error,
            }
        except Exception:
            if idempotency_key:
                async with SessionLocal() as db:
                    await InboundIdempotencyService(db).release_failed(idempotency_key)
            raise

    async with SessionLocal() as db:
        try:
            result = await InboundRouter(db).process(event, background_tasks=background_tasks)
            if idempotency_key:
                await InboundIdempotencyService(db).mark_completed(idempotency_key, commit=False)
            await db.commit()
            return result
        except Exception:
            await db.rollback()
            if idempotency_key:
                await InboundIdempotencyService(db).release_failed(idempotency_key)
            raise


def _authenticate_waha_webhook(request: Request) -> None:
    if settings.environment.strip().lower() != "production":
        return
    expected = settings.waha_api_key.strip()
    if not expected:
        raise HTTPException(status_code=503, detail="WAHA webhook authentication is not configured")
    supplied = (request.headers.get("X-Api-Key") or "").strip()
    if supplied != expected:
        raise HTTPException(status_code=401, detail="Invalid WAHA webhook authentication")


def _validate_waha_session(event: dict[str, Any]) -> None:
    event_session = str(event.get("session") or "").strip()
    configured = settings.waha_session_name.strip()
    if event_session and configured and event_session != configured:
        raise HTTPException(status_code=403, detail="Unexpected WAHA session")


def _is_from_me(payload: dict[str, Any]) -> bool:
    return bool(payload.get("fromMe"))


def _resolve_chat_id(payload: dict[str, Any]) -> str | None:
    for value in (payload.get("chatId"), payload.get("to"), payload.get("from")):
        text = str(value or "").strip()
        if text:
            return text
    return None


def _is_group_chat(chat_id: str) -> bool:
    value = str(chat_id or "").lower()
    return value.endswith("@g.us") or value == "status@broadcast" or value.endswith("@newsletter") or value.endswith("@broadcast")


async def _plan_owner_natural_action(
    db: AsyncSession,
    *,
    event: dict[str, Any],
    message_id: str | None,
    request_id: str,
) -> dict[str, Any] | None:
    normalized = MessageNormalizer().normalize(event)
    if not normalized.message_text:
        return None
    admin = await AdminManagementService(db).resolve_admin_message(normalized)
    if not admin:
        return None
    try:
        result = await NaturalActionPlannerService(db).plan_and_execute(
            instruction=normalized.message_text,
            requested_by_contact_id=admin.contact_id,
            permission_level=admin.permission_level,
            source_message_id=message_id,
            idempotency_key=f"waha:{request_id}:{message_id or 'unknown'}",
        )
        return result
    except ValueError as exc:
        return {"error": str(exc)}

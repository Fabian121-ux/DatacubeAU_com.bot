from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.outbound_authorization_service import OutboundAuthorizationService
from app.models.scheduled_action import ScheduledAction
from app.models.schema import AuditLog, OutboundMessage
from app.services.contact_intelligence_service import ContactIntelligenceService
from app.utils.time import utcnow


SUPPORTED_ACTIONS = {"whatsapp.send_message"}
ACTIVE_STATUSES = {"scheduled", "paused"}


class ScheduledActionService:
    """Durable action scheduler that hands due WhatsApp work to the existing outbound queue."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.contacts = ContactIntelligenceService(session)

    async def create_whatsapp_message(
        self,
        *,
        target_reference: str,
        text: str,
        scheduled_for: datetime,
        timezone: str,
        source_message_id: int | None = None,
        requested_by_contact_id: int | None = None,
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        message_text = (text or "").strip()
        if not message_text:
            raise ValueError("message text is required")
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            raise ValueError("scheduled_for must include a timezone offset")

        resolution = await self.contacts.resolve(target_reference)
        if resolution.get("status") != "resolved" or not resolution.get("match"):
            error = ValueError("target contact is ambiguous" if resolution.get("status") == "ambiguous" else "target contact not found")
            setattr(error, "resolution", resolution)
            raise error
        match = resolution["match"]

        action = ScheduledAction(
            action_type="whatsapp.send_message",
            target_contact_id=match["contact_id"],
            target_chat_id=match["whatsapp_id"],
            payload_json={"text": message_text},
            timezone=(timezone or "UTC")[:80],
            scheduled_for=scheduled_for,
            status="scheduled",
            is_enabled=True,
            retry_count=0,
            max_retries=3,
            source_message_id=source_message_id,
            requested_by_contact_id=requested_by_contact_id,
            idempotency_key=(idempotency_key or f"zina-action-{uuid4().hex}")[:160],
            metadata_json={
                "contact_resolution": {
                    "confidence": resolution.get("confidence"),
                    "margin": resolution.get("margin"),
                    "matched_field": match.get("matched_field"),
                }
            },
            updated_at=utcnow(),
        )
        self.session.add(action)
        await self.session.flush()
        self._audit("scheduled_action_created", action, {"scheduled_for": scheduled_for.isoformat()})
        return self.serialize(action)

    async def list(self, *, status: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        stmt = select(ScheduledAction)
        if status:
            stmt = stmt.where(ScheduledAction.status == status)
        rows = (
            await self.session.execute(
                stmt.order_by(ScheduledAction.scheduled_for.asc(), ScheduledAction.id.asc()).limit(max(1, min(limit, 200)))
            )
        ).scalars().all()
        return [self.serialize(row) for row in rows]

    async def get(self, action_id: int) -> ScheduledAction:
        row = await self.session.get(ScheduledAction, action_id)
        if not row:
            raise ValueError("scheduled action not found")
        return row

    async def cancel(self, action_id: int) -> dict[str, Any]:
        row = await self.get(action_id)
        if row.status not in ACTIVE_STATUSES:
            raise ValueError(f"cannot cancel action in status {row.status}")
        row.status = "cancelled"
        row.is_enabled = False
        row.cancelled_at = utcnow()
        row.updated_at = utcnow()
        self._audit("scheduled_action_cancelled", row)
        await self.session.flush()
        return self.serialize(row)

    async def pause(self, action_id: int) -> dict[str, Any]:
        row = await self.get(action_id)
        if row.status != "scheduled":
            raise ValueError(f"cannot pause action in status {row.status}")
        row.status = "paused"
        row.updated_at = utcnow()
        self._audit("scheduled_action_paused", row)
        await self.session.flush()
        return self.serialize(row)

    async def resume(self, action_id: int) -> dict[str, Any]:
        row = await self.get(action_id)
        if row.status != "paused":
            raise ValueError(f"cannot resume action in status {row.status}")
        row.status = "scheduled"
        row.is_enabled = True
        row.updated_at = utcnow()
        self._audit("scheduled_action_resumed", row)
        await self.session.flush()
        return self.serialize(row)

    async def reschedule(self, action_id: int, *, scheduled_for: datetime, timezone: str | None = None) -> dict[str, Any]:
        if scheduled_for.tzinfo is None or scheduled_for.utcoffset() is None:
            raise ValueError("scheduled_for must include a timezone offset")
        row = await self.get(action_id)
        if row.status not in ACTIVE_STATUSES:
            raise ValueError(f"cannot reschedule action in status {row.status}")
        row.scheduled_for = scheduled_for
        row.status = "scheduled"
        row.is_enabled = True
        if timezone:
            row.timezone = timezone[:80]
        row.updated_at = utcnow()
        self._audit("scheduled_action_rescheduled", row, {"scheduled_for": scheduled_for.isoformat()})
        await self.session.flush()
        return self.serialize(row)

    async def run_now(self, action_id: int) -> dict[str, Any]:
        row = await self.get(action_id)
        if row.status not in ACTIVE_STATUSES:
            raise ValueError(f"cannot run action in status {row.status}")
        row.scheduled_for = utcnow()
        row.status = "scheduled"
        row.is_enabled = True
        row.updated_at = utcnow()
        self._audit("scheduled_action_run_now_requested", row)
        await self.session.flush()
        return self.serialize(row)

    async def release_due(self, *, limit: int = 25) -> int:
        now = utcnow()
        rows = (
            await self.session.execute(
                select(ScheduledAction)
                .where(ScheduledAction.status == "scheduled")
                .where(ScheduledAction.is_enabled.is_(True))
                .where(ScheduledAction.scheduled_for <= now)
                .order_by(ScheduledAction.scheduled_for.asc(), ScheduledAction.id.asc())
                .limit(max(1, min(limit, 100)))
                .with_for_update(skip_locked=True)
            )
        ).scalars().all()
        released = 0
        for row in rows:
            if row.action_type not in SUPPORTED_ACTIONS:
                row.status = "failed"
                row.last_error = f"unsupported action type: {row.action_type}"
                row.updated_at = now
                self._audit("scheduled_action_failed", row, {"error": row.last_error})
                continue
            text = str((row.payload_json or {}).get("text") or "").strip()
            if not text:
                row.status = "failed"
                row.last_error = "missing message text"
                row.updated_at = now
                self._audit("scheduled_action_failed", row, {"error": row.last_error})
                continue

            outbound = OutboundMessage(
                chat_id=row.target_chat_id,
                message_text=text,
                status="pending",
                retry_count=0,
                max_retries=row.max_retries,
                next_attempt_at=now,
                formatting_json={"scheduled_action_id": row.id},
                updated_at=now,
            )
            self.session.add(outbound)
            await self.session.flush()
            # A scheduled action may target the owner or an external contact. Only the
            # owner-destined case is authorized by destination at the delivery fence and
            # therefore needs the payload stamp; external rows keep the existing durable
            # scheduled-action binding as their authority.
            if OutboundAuthorizationService.is_owner_destination(outbound.chat_id):
                outbound.formatting_json = OutboundAuthorizationService.stamp_owner_payload(outbound)
                await self.session.flush()
            row.outbound_queue_id = outbound.id
            row.status = "queued"
            row.executed_at = now
            row.last_error = None
            row.updated_at = now
            released += 1
            self._audit("scheduled_action_queued", row, {"outbound_queue_id": outbound.id})
        await self.session.flush()
        return released

    async def reconcile_outbound_delivery(self, outbound: OutboundMessage) -> dict[str, Any] | None:
        """Project the authoritative outbound queue result back onto its scheduled action."""
        if not outbound.id:
            return None
        row = (
            await self.session.execute(
                select(ScheduledAction)
                .where(ScheduledAction.outbound_queue_id == outbound.id)
                .limit(1)
                .with_for_update()
            )
        ).scalar_one_or_none()
        if not row:
            return None

        now = utcnow()
        previous_status = row.status
        row.retry_count = int(outbound.retry_count or 0)
        row.last_error = outbound.error_message
        row.updated_at = now
        metadata = dict(row.metadata_json or {})
        delivery = dict(metadata.get("delivery") or {})
        delivery.update(
            {
                "outbound_queue_id": outbound.id,
                "status": outbound.status,
                "retry_count": row.retry_count,
                "updated_at": now.isoformat(),
            }
        )

        if outbound.status == "sent":
            row.status = "completed"
            row.is_enabled = False
            row.last_error = None
            delivery["completed_at"] = now.isoformat()
            if previous_status != "completed":
                self._audit(
                    "scheduled_action_completed",
                    row,
                    {"outbound_queue_id": outbound.id, "retry_count": row.retry_count},
                )
        elif outbound.status == "failed":
            row.status = "failed"
            row.is_enabled = False
            delivery["failed_at"] = now.isoformat()
            if previous_status != "failed":
                self._audit(
                    "scheduled_action_delivery_failed",
                    row,
                    {
                        "outbound_queue_id": outbound.id,
                        "retry_count": row.retry_count,
                        "max_retries": outbound.max_retries,
                    },
                )
        elif outbound.status == "retrying":
            row.status = "queued"
            self._audit(
                "scheduled_action_delivery_retrying",
                row,
                {
                    "outbound_queue_id": outbound.id,
                    "retry_count": row.retry_count,
                    "max_retries": outbound.max_retries,
                },
            )

        metadata["delivery"] = delivery
        row.metadata_json = metadata
        await self.session.flush()
        return self.serialize(row)

    def _audit(self, action: str, row: ScheduledAction, details: dict[str, Any] | None = None) -> None:
        self.session.add(
            AuditLog(
                action=action,
                entity_type="scheduled_actions",
                entity_id=str(row.id) if row.id else None,
                details_json={
                    "action_type": row.action_type,
                    "target_contact_id": row.target_contact_id,
                    "target_chat_id": row.target_chat_id,
                    "status": row.status,
                    **(details or {}),
                },
            )
        )

    @staticmethod
    def serialize(row: ScheduledAction) -> dict[str, Any]:
        return {
            "id": row.id,
            "action_type": row.action_type,
            "target_contact_id": row.target_contact_id,
            "target_chat_id": row.target_chat_id,
            "payload": row.payload_json,
            "timezone": row.timezone,
            "scheduled_for": row.scheduled_for,
            "status": row.status,
            "is_enabled": row.is_enabled,
            "retry_count": row.retry_count,
            "max_retries": row.max_retries,
            "source_message_id": row.source_message_id,
            "requested_by_contact_id": row.requested_by_contact_id,
            "outbound_queue_id": row.outbound_queue_id,
            "idempotency_key": row.idempotency_key,
            "last_error": row.last_error,
            "metadata": row.metadata_json or {},
            "created_at": row.created_at,
            "updated_at": row.updated_at,
            "executed_at": row.executed_at,
            "cancelled_at": row.cancelled_at,
        }

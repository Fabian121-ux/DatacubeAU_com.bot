from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.conversation_takeover import ConversationTakeover
from app.models.schema import AuditLog, OutboundMessage
from app.services.bot_config_service import BotConfigService
from app.utils.time import utcnow


HANDOFF_TEMPLATE = "It looks like {owner_name} is busy. I'm {assistant_name}, his assistant — you can continue with me here."
DEFERRED_STATUS = "deferred"
CANCELLED_STATUS = "cancelled"


class ConversationTakeoverService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.config = BotConfigService(session)

    async def get_chat_control(self, *, chat_id: str) -> dict[str, object]:
        row = await self._get_locked(chat_id)
        if row is None:
            threshold = max(5, await self.config.get_int("auto_assist_inactivity_seconds", 120))
            return {
                "chat_id": chat_id,
                "state": "fabian_active",
                "auto_assist_enabled": True,
                "wait_for_fabian_first": await self.config.get_bool("auto_assist_wait_for_fabian_first", False),
                "inactivity_seconds": threshold,
                "takeover_due_at": None,
                "assisting_since": None,
                "last_transition_reason": None,
            }
        return self._serialize_control(row)

    async def set_chat_control(
        self,
        *,
        chat_id: str,
        auto_assist_enabled: bool,
        inactivity_seconds: int | None = None,
        wait_for_fabian_first: bool | None = None,
    ) -> dict[str, object]:
        now = utcnow()
        threshold = max(5, inactivity_seconds or await self.config.get_int("auto_assist_inactivity_seconds", 120))
        row = await self._get_locked(chat_id)
        if row is None:
            policy_enabled = (
                wait_for_fabian_first
                if wait_for_fabian_first is not None
                else await self.config.get_bool("auto_assist_wait_for_fabian_first", False)
            )
            row = ConversationTakeover(
                chat_id=chat_id,
                state="fabian_active" if auto_assist_enabled else "do_not_auto_assist",
                auto_assist_enabled=auto_assist_enabled,
                inactivity_seconds=threshold,
                metadata_json={"wait_for_fabian_first": bool(policy_enabled)},
                updated_at=now,
            )
            self.session.add(row)
        else:
            metadata = dict(row.metadata_json or {})
            if wait_for_fabian_first is not None:
                metadata["wait_for_fabian_first"] = bool(wait_for_fabian_first)
            row.metadata_json = metadata
            row.auto_assist_enabled = auto_assist_enabled
            row.inactivity_seconds = threshold
            if not auto_assist_enabled:
                row.state = "do_not_auto_assist"
                row.pending_since = None
                row.takeover_due_at = None
                row.assisting_since = None
                row.handoff_sent_at = None
                row.last_transition_reason = "admin_auto_assist_disabled"
                await self._cancel_deferred_for_chat(chat_id, reason="admin_auto_assist_disabled")
            elif row.state == "do_not_auto_assist":
                row.state = "fabian_active"
                row.last_transition_reason = "admin_auto_assist_enabled"
            row.updated_at = now
        self.session.add(
            AuditLog(
                action="conversation_takeover_control_updated",
                entity_type="conversation_takeover",
                entity_id=chat_id,
                details_json={
                    "chat_id": chat_id,
                    "auto_assist_enabled": auto_assist_enabled,
                    "wait_for_fabian_first": self._wait_policy_enabled(row),
                    "inactivity_seconds": threshold,
                },
            )
        )
        await self.session.flush()
        return self._serialize_control(row)

    async def should_wait_for_fabian_first(self, *, chat_id: str) -> bool:
        if not await self.config.get_bool("auto_assist_enabled", True):
            return False
        row = await self._get(chat_id)
        if row is None:
            return await self.config.get_bool("auto_assist_wait_for_fabian_first", False)
        if not row.auto_assist_enabled or row.state in {"do_not_auto_assist", "zina_assisting"}:
            return False
        return self._wait_policy_enabled(row)

    async def schedule_if_eligible(
        self,
        *,
        chat_id: str,
        chat_type: str,
        message_id: str | None,
        router_replied: bool,
        reply_deferred: bool = False,
        outbound_queue_id: int | None = None,
    ) -> bool:
        if chat_type != "dm" or (router_replied and not reply_deferred):
            return False
        if not await self.config.get_bool("auto_assist_enabled", True):
            return False

        threshold = max(5, await self.config.get_int("auto_assist_inactivity_seconds", 120))
        now = utcnow()
        row = await self._get_locked(chat_id)
        if row is None:
            row = ConversationTakeover(
                chat_id=chat_id,
                state="fabian_active",
                auto_assist_enabled=True,
                inactivity_seconds=threshold,
                metadata_json={
                    "wait_for_fabian_first": await self.config.get_bool(
                        "auto_assist_wait_for_fabian_first",
                        False,
                    )
                },
                updated_at=now,
            )
            self.session.add(row)

        if not row.auto_assist_enabled or row.state == "do_not_auto_assist":
            if reply_deferred and outbound_queue_id:
                await self._cancel_deferred_queue(outbound_queue_id, reason="auto_assist_disabled")
            return False
        if row.state == "zina_assisting":
            row.last_inbound_message_id = message_id
            row.updated_at = now
            if reply_deferred and outbound_queue_id:
                await self._release_deferred_queue(outbound_queue_id, release_at=now)
            await self.session.flush()
            return False

        if reply_deferred and outbound_queue_id:
            await self._cancel_deferred_for_chat(
                chat_id,
                reason="superseded_by_newer_inbound",
                exclude_queue_id=outbound_queue_id,
            )

        threshold = max(5, row.inactivity_seconds or threshold)
        metadata = dict(row.metadata_json or {})
        if reply_deferred and outbound_queue_id:
            metadata["deferred_outbound_queue_id"] = outbound_queue_id
        else:
            metadata.pop("deferred_outbound_queue_id", None)
        row.metadata_json = metadata
        row.state = "waiting_for_fabian"
        row.inactivity_seconds = threshold
        row.pending_since = now
        row.takeover_due_at = now + timedelta(seconds=threshold)
        row.last_inbound_message_id = message_id
        row.assisting_since = None
        row.handoff_sent_at = None
        row.last_transition_reason = (
            "inbound_dm_deferred_for_fabian" if reply_deferred else "inbound_dm_without_reply"
        )
        row.updated_at = now
        self.session.add(
            AuditLog(
                action="conversation_takeover_waiting",
                entity_type="conversation_takeover",
                entity_id=chat_id,
                details_json={
                    "chat_id": chat_id,
                    "message_id": message_id,
                    "inactivity_seconds": threshold,
                    "reply_deferred": reply_deferred,
                    "outbound_queue_id": outbound_queue_id,
                },
            )
        )
        await self.session.flush()
        return True

    async def record_owner_reply(self, *, chat_id: str) -> bool:
        row = await self._get_locked(chat_id)
        if row is None:
            return False
        now = utcnow()
        previous_state = row.state
        row.state = "fabian_resumed" if previous_state in {"waiting_for_fabian", "zina_assisting"} else "fabian_active"
        if not row.auto_assist_enabled:
            row.state = "do_not_auto_assist"
        row.last_owner_message_at = now
        row.takeover_due_at = None
        row.pending_since = None
        row.last_transition_reason = "owner_message_detected"
        row.updated_at = now
        cancelled_deferred = await self._cancel_deferred_for_chat(chat_id, reason="owner_message_detected")
        metadata = dict(row.metadata_json or {})
        metadata.pop("deferred_outbound_queue_id", None)
        row.metadata_json = metadata
        self.session.add(
            AuditLog(
                action="conversation_takeover_cancelled",
                entity_type="conversation_takeover",
                entity_id=chat_id,
                details_json={
                    "chat_id": chat_id,
                    "previous_state": previous_state,
                    "new_state": row.state,
                    "cancelled_deferred_replies": cancelled_deferred,
                },
            )
        )
        await self.session.flush()
        return previous_state in {"waiting_for_fabian", "zina_assisting"} or cancelled_deferred > 0

    async def claim_due(self, *, limit: int = 20) -> int:
        now = utcnow()
        stmt = (
            select(ConversationTakeover)
            .where(ConversationTakeover.state == "waiting_for_fabian")
            .where(ConversationTakeover.auto_assist_enabled.is_(True))
            .where(ConversationTakeover.takeover_due_at.is_not(None))
            .where(ConversationTakeover.takeover_due_at <= now)
            .order_by(ConversationTakeover.takeover_due_at, ConversationTakeover.id)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        if not rows:
            return 0

        cfg = await self.config.get_all()
        owner_name = (cfg.get("owner_name") or "Fabian").strip() or "Fabian"
        assistant_name = (cfg.get("assistant_name") or "Zina").strip() or "Zina"
        configured_text = (cfg.get("auto_assist_handoff_text") or "").strip()
        handoff_text = configured_text or HANDOFF_TEMPLATE.format(owner_name=owner_name, assistant_name=assistant_name)

        claimed = 0
        for row in rows:
            if row.last_owner_message_at and row.pending_since and row.last_owner_message_at >= row.pending_since:
                row.state = "fabian_resumed"
                row.takeover_due_at = None
                row.last_transition_reason = "owner_replied_before_takeover"
                row.updated_at = now
                await self._cancel_deferred_for_chat(row.chat_id, reason="owner_replied_before_takeover")
                metadata = dict(row.metadata_json or {})
                metadata.pop("deferred_outbound_queue_id", None)
                row.metadata_json = metadata
                continue

            row.state = "zina_assisting"
            row.assisting_since = now
            row.handoff_sent_at = now
            row.takeover_due_at = None
            row.last_transition_reason = "inactivity_threshold_elapsed"
            row.updated_at = now
            outbound = OutboundMessage(
                chat_id=row.chat_id,
                message_text=handoff_text,
                status="pending",
                next_attempt_at=now,
                formatting_json={"source": "conversation_takeover", "transparent_assistant_handoff": True},
            )
            self.session.add(outbound)

            metadata = dict(row.metadata_json or {})
            deferred_queue_id = metadata.pop("deferred_outbound_queue_id", None)
            released_deferred = False
            if deferred_queue_id:
                released_deferred = await self._release_deferred_queue(
                    int(deferred_queue_id),
                    release_at=now + timedelta(seconds=1),
                )
            row.metadata_json = metadata
            self.session.add(
                AuditLog(
                    action="conversation_takeover_started",
                    entity_type="conversation_takeover",
                    entity_id=row.chat_id,
                    details_json={
                        "chat_id": row.chat_id,
                        "inactivity_seconds": row.inactivity_seconds,
                        "last_inbound_message_id": row.last_inbound_message_id,
                        "released_deferred_reply": released_deferred,
                        "deferred_outbound_queue_id": deferred_queue_id,
                    },
                )
            )
            claimed += 1

        await self.session.flush()
        return claimed

    async def _cancel_deferred_for_chat(
        self,
        chat_id: str,
        *,
        reason: str,
        exclude_queue_id: int | None = None,
    ) -> int:
        stmt = (
            select(OutboundMessage)
            .where(OutboundMessage.chat_id == chat_id)
            .where(OutboundMessage.status == DEFERRED_STATUS)
            .with_for_update()
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        cancelled = 0
        now = utcnow()
        for outbound in rows:
            if exclude_queue_id is not None and outbound.id == exclude_queue_id:
                continue
            outbound.status = CANCELLED_STATUS
            outbound.error_message = reason[:2000]
            outbound.updated_at = now
            cancelled += 1
        return cancelled

    async def _cancel_deferred_queue(self, queue_id: int, *, reason: str) -> bool:
        stmt = (
            select(OutboundMessage)
            .where(OutboundMessage.id == queue_id)
            .where(OutboundMessage.status == DEFERRED_STATUS)
            .limit(1)
            .with_for_update()
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        row.status = CANCELLED_STATUS
        row.error_message = reason[:2000]
        row.updated_at = utcnow()
        return True

    async def _release_deferred_queue(self, queue_id: int, *, release_at) -> bool:
        stmt = (
            select(OutboundMessage)
            .where(OutboundMessage.id == queue_id)
            .where(OutboundMessage.status == DEFERRED_STATUS)
            .limit(1)
            .with_for_update()
        )
        row = (await self.session.execute(stmt)).scalar_one_or_none()
        if row is None:
            return False
        row.status = "pending"
        row.next_attempt_at = release_at
        row.error_message = None
        row.updated_at = utcnow()
        formatting = dict(row.formatting_json or {})
        formatting["released_by_conversation_takeover"] = True
        row.formatting_json = formatting
        return True

    @staticmethod
    def _wait_policy_enabled(row: ConversationTakeover) -> bool:
        metadata = row.metadata_json or {}
        return bool(metadata.get("wait_for_fabian_first", False))

    @staticmethod
    def _serialize_control(row: ConversationTakeover) -> dict[str, object]:
        return {
            "chat_id": row.chat_id,
            "state": row.state,
            "auto_assist_enabled": row.auto_assist_enabled,
            "wait_for_fabian_first": ConversationTakeoverService._wait_policy_enabled(row),
            "inactivity_seconds": row.inactivity_seconds,
            "takeover_due_at": row.takeover_due_at,
            "assisting_since": row.assisting_since,
            "last_transition_reason": row.last_transition_reason,
        }

    async def _get(self, chat_id: str) -> ConversationTakeover | None:
        stmt = select(ConversationTakeover).where(ConversationTakeover.chat_id == chat_id).limit(1)
        return (await self.session.execute(stmt)).scalar_one_or_none()

    async def _get_locked(self, chat_id: str) -> ConversationTakeover | None:
        stmt = (
            select(ConversationTakeover)
            .where(ConversationTakeover.chat_id == chat_id)
            .limit(1)
            .with_for_update()
        )
        return (await self.session.execute(stmt)).scalar_one_or_none()

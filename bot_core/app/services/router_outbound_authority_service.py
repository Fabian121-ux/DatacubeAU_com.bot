from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.outbound_authorization_service import (
    AuthorizationContext,
    OutboundAuthorizationService,
)


@dataclass(frozen=True, slots=True)
class PreparedExternalReply:
    approval_id: int
    context: AuthorizationContext


class RouterOutboundAuthorityService:
    """Prepare an ordinary external router reply for durable OWNER authorization.

    This component deliberately does not send, requeue, approve, or infer authority.
    It stamps the exact durable context required by the final Outbound Queue fence,
    coalesces only a short same-contact/text-only pending burst, and creates exactly
    one pending single-use approval for the surviving candidate.
    """

    _BURST_WINDOW_SECONDS = 4

    def __init__(self, session: AsyncSession):
        self.session = session
        self.authorization = OutboundAuthorizationService(session)

    async def prepare_external_reply(
        self,
        queue_message,
        *,
        inbound_message_id: int,
        contact_id: int,
        response_category: str = "normal_reply",
    ) -> PreparedExternalReply:
        queue_id = int(getattr(queue_message, "id", 0) or 0)
        target_chat_id = str(getattr(queue_message, "chat_id", "") or "").strip()
        message_text = str(getattr(queue_message, "message_text", "") or "")
        category = str(response_category or "normal_reply").strip().lower() or "normal_reply"
        if queue_id <= 0:
            raise ValueError("outbound queue row must be flushed before authority preparation")
        if int(inbound_message_id) <= 0 or int(contact_id) <= 0:
            raise ValueError("exact inbound message and contact identifiers are required")
        if not target_chat_id:
            raise ValueError("exact target chat is required")

        source_inbound_message_ids = await self._coalesce_recent_pending(
            queue_message,
            inbound_message_id=int(inbound_message_id),
            contact_id=int(contact_id),
            target_chat_id=target_chat_id,
            response_category=category,
        )
        if not source_inbound_message_ids:
            source_inbound_message_ids = [int(inbound_message_id)]

        content_sha256 = self.authorization.content_hash(message_text)
        metadata = dict(queue_message.formatting_json) if isinstance(queue_message.formatting_json, dict) else {}
        metadata.update(
            {
                "delivery_policy": "approval_required",
                "reply_deferred": True,
                "inbound_message_id": int(inbound_message_id),
                "source_inbound_message_ids": source_inbound_message_ids,
                "contact_id": int(contact_id),
                "response_category": category,
                "content_sha256": content_sha256,
            }
        )
        queue_message.formatting_json = metadata
        queue_message.status = "deferred"

        context = AuthorizationContext(
            outbound_queue_id=queue_id,
            inbound_message_id=int(inbound_message_id),
            contact_id=int(contact_id),
            target_chat_id=target_chat_id,
            content_sha256=content_sha256,
            response_category=category,
        )
        approval_id = await self.authorization.create_pending_approval(context=context)
        return PreparedExternalReply(approval_id=approval_id, context=context)

    async def _coalesce_recent_pending(
        self,
        queue_message,
        *,
        inbound_message_id: int,
        contact_id: int,
        target_chat_id: str,
        response_category: str,
    ) -> list[int]:
        """Supersede at most one immediately preceding same-contact draft.

        PostgreSQL transaction advisory locking serializes only the exact durable
        contact/chat burst. Other contacts never share the lock or candidate query.
        Media candidates are intentionally excluded so coalescing cannot discard an
        attachment. The newest draft survives; every trusted constituent source ID is
        carried forward for auditability while the old approval is rejected.
        """
        current_id = int(getattr(queue_message, "id", 0) or 0)
        if getattr(queue_message, "media_url", None) or getattr(queue_message, "media_type", None):
            return [inbound_message_id]

        lock_key = f"p0-burst:{contact_id}:{target_chat_id}"
        await self.session.execute(text("SELECT pg_advisory_xact_lock(hashtext(:lock_key))"), {"lock_key": lock_key})
        result = await self.session.execute(
            text(
                """
                SELECT q.id AS queue_id, q.formatting_json, a.id AS approval_id
                FROM outbound_queue q
                JOIN outbound_approvals a ON a.outbound_queue_id = q.id
                WHERE q.id <> :current_id
                  AND q.chat_id = :target_chat_id
                  AND q.status = 'deferred'
                  AND q.media_url IS NULL
                  AND q.media_type IS NULL
                  AND a.status = 'pending'
                  AND a.expires_at > now()
                  AND q.created_at >= now() - (:burst_seconds * interval '1 second')
                  AND (q.formatting_json ->> 'contact_id') = :contact_id
                  AND lower(COALESCE(q.formatting_json ->> 'response_category', 'normal_reply')) = :response_category
                ORDER BY q.created_at DESC, q.id DESC
                LIMIT 1
                FOR UPDATE OF q, a
                """
            ),
            {
                "current_id": current_id,
                "target_chat_id": target_chat_id,
                "contact_id": str(contact_id),
                "response_category": response_category,
                "burst_seconds": self._BURST_WINDOW_SECONDS,
            },
        )
        row = result.mappings().first()
        if not isinstance(row, Mapping):
            return [inbound_message_id]

        previous_ids = self._trusted_source_ids(row.get("formatting_json"), contact_id=contact_id, target_chat_id=target_chat_id)
        combined = self._merge_source_ids(previous_ids, [inbound_message_id])
        await self.session.execute(
            text(
                """
                UPDATE outbound_approvals
                SET status = 'rejected', rejected_at = now(), updated_at = now()
                WHERE id = :approval_id AND status = 'pending'
                """
            ),
            {"approval_id": int(row["approval_id"])},
        )
        await self.session.execute(
            text(
                """
                UPDATE outbound_queue
                SET status = 'superseded',
                    error_message = 'coalesced into newer same-contact deferred candidate',
                    updated_at = now()
                WHERE id = :queue_id AND status = 'deferred'
                """
            ),
            {"queue_id": int(row["queue_id"])},
        )
        return combined

    @staticmethod
    def _trusted_source_ids(metadata, *, contact_id: int, target_chat_id: str) -> list[int]:
        if not isinstance(metadata, dict):
            return []
        try:
            metadata_contact_id = int(metadata.get("contact_id"))
        except (TypeError, ValueError):
            return []
        if metadata_contact_id != contact_id:
            return []
        values = metadata.get("source_inbound_message_ids")
        if not isinstance(values, list):
            values = [metadata.get("inbound_message_id")]
        result: list[int] = []
        for value in values:
            try:
                parsed = int(value)
            except (TypeError, ValueError):
                continue
            if parsed > 0 and parsed not in result:
                result.append(parsed)
        return result

    @staticmethod
    def _merge_source_ids(*groups: list[int]) -> list[int]:
        merged: list[int] = []
        for group in groups:
            for value in group:
                parsed = int(value)
                if parsed > 0 and parsed not in merged:
                    merged.append(parsed)
        return merged

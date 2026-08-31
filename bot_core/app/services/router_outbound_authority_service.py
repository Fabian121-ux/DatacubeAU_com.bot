from __future__ import annotations

from dataclasses import dataclass

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
    It only stamps the exact durable context required by the final Outbound Queue fence
    and creates the corresponding pending single-use approval record.
    """

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

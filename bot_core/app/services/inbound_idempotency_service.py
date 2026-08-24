from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True, frozen=True)
class InboundReceipt:
    event_key: str
    session_name: str | None
    chat_id: str | None
    message_id: str | None


class InboundIdempotencyService:
    """Durably claim WAHA inbound events before routing side effects occur."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def claim(self, receipt: InboundReceipt) -> bool:
        result = await self.session.execute(
            text(
                """
                INSERT INTO inbound_webhook_receipts (
                    event_key,
                    session_name,
                    chat_id,
                    message_id,
                    status,
                    updated_at
                )
                VALUES (
                    :event_key,
                    :session_name,
                    :chat_id,
                    :message_id,
                    'processing',
                    NOW()
                )
                ON CONFLICT (event_key) DO NOTHING
                RETURNING id
                """
            ),
            {
                "event_key": receipt.event_key,
                "session_name": receipt.session_name,
                "chat_id": receipt.chat_id,
                "message_id": receipt.message_id,
            },
        )
        claimed = result.scalar_one_or_none() is not None
        await self.session.commit()
        return claimed

    async def mark_completed(self, event_key: str) -> None:
        await self.session.execute(
            text(
                """
                UPDATE inbound_webhook_receipts
                SET status = 'completed', updated_at = NOW()
                WHERE event_key = :event_key
                """
            ),
            {"event_key": event_key},
        )
        await self.session.commit()

    async def release_failed(self, event_key: str) -> None:
        """Release a failed claim so a later WAHA retry may safely reprocess it."""
        await self.session.execute(
            text(
                """
                DELETE FROM inbound_webhook_receipts
                WHERE event_key = :event_key AND status = 'processing'
                """
            ),
            {"event_key": event_key},
        )
        await self.session.commit()

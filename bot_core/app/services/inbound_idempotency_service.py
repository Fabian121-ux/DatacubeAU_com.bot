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

    # A worker can die after committing a claim but before finishing command routing.
    # WAHA retries must be able to reclaim that abandoned work instead of treating it
    # as a permanent duplicate. Five minutes is comfortably above normal webhook work
    # while still allowing bounded crash recovery.
    PROCESSING_LEASE_SECONDS = 300

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
                ON CONFLICT (event_key) DO UPDATE
                SET session_name = EXCLUDED.session_name,
                    chat_id = EXCLUDED.chat_id,
                    message_id = EXCLUDED.message_id,
                    status = 'processing',
                    updated_at = NOW()
                WHERE inbound_webhook_receipts.status = 'processing'
                  AND inbound_webhook_receipts.updated_at
                      < NOW() - (:lease_seconds * INTERVAL '1 second')
                RETURNING id
                """
            ),
            {
                "event_key": receipt.event_key,
                "session_name": receipt.session_name,
                "chat_id": receipt.chat_id,
                "message_id": receipt.message_id,
                "lease_seconds": self.PROCESSING_LEASE_SECONDS,
            },
        )
        claimed = result.scalar_one_or_none() is not None
        await self.session.commit()
        return claimed

    async def mark_completed(self, event_key: str, *, commit: bool = True) -> None:
        """Mark a claim completed, optionally inside the caller's transaction.

        Command-control side effects use commit=False so durable side effects and the
        receipt completion are committed atomically. Background routing retains the
        historical commit=True behavior.
        """
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
        if commit:
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

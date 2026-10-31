from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(slots=True, frozen=True)
class InboundReceipt:
    event_key: str
    session_name: str | None
    chat_id: str | None
    message_id: str | None


class InboundClaimLostError(RuntimeError):
    """Raised when a worker no longer owns the durable inbound receipt lease."""


# The durable claim token lives in PostgreSQL. This task-local mapping only carries
# the lease credential from claim() to completion/release without widening every
# routing function signature. Context is propagated to FastAPI/Starlette background
# work, and values are replaced rather than mutated so concurrent tasks do not share
# a writable mapping.
_claim_tokens: ContextVar[dict[str, str]] = ContextVar("inbound_claim_tokens", default={})


class InboundIdempotencyService:
    """Durably claim WAHA inbound events before routing side effects occur."""

    # A worker can die after committing a claim but before finishing command routing.
    # WAHA retries may reclaim abandoned work after this lease. Each claim has a
    # generation token so the original worker cannot complete/delete a replacement
    # worker's claim if the original operation legitimately runs beyond the lease.
    PROCESSING_LEASE_SECONDS = 300

    def __init__(self, session: AsyncSession):
        self.session = session

    @staticmethod
    def _remember_token(event_key: str, claim_token: str) -> None:
        current = _claim_tokens.get()
        _claim_tokens.set({**current, event_key: claim_token})

    @staticmethod
    def _token_for(event_key: str) -> str | None:
        return _claim_tokens.get().get(event_key)

    @staticmethod
    def _forget_token(event_key: str, claim_token: str | None) -> None:
        current = _claim_tokens.get()
        if not claim_token or current.get(event_key) != claim_token:
            return
        updated = dict(current)
        updated.pop(event_key, None)
        _claim_tokens.set(updated)

    async def claim(self, receipt: InboundReceipt) -> bool:
        claim_token = str(uuid4())
        result = await self.session.execute(
            text(
                """
                INSERT INTO inbound_webhook_receipts (
                    event_key,
                    session_name,
                    chat_id,
                    message_id,
                    status,
                    claim_token,
                    updated_at
                )
                VALUES (
                    :event_key,
                    :session_name,
                    :chat_id,
                    :message_id,
                    'processing',
                    :claim_token,
                    NOW()
                )
                ON CONFLICT (event_key) DO UPDATE
                SET session_name = EXCLUDED.session_name,
                    chat_id = EXCLUDED.chat_id,
                    message_id = EXCLUDED.message_id,
                    status = 'processing',
                    claim_token = EXCLUDED.claim_token,
                    updated_at = NOW()
                WHERE inbound_webhook_receipts.status = 'processing'
                  AND inbound_webhook_receipts.updated_at
                      < NOW() - (:lease_seconds * INTERVAL '1 second')
                RETURNING claim_token
                """
            ),
            {
                "event_key": receipt.event_key,
                "session_name": receipt.session_name,
                "chat_id": receipt.chat_id,
                "message_id": receipt.message_id,
                "claim_token": claim_token,
                "lease_seconds": self.PROCESSING_LEASE_SECONDS,
            },
        )
        returned_token = result.scalar_one_or_none()
        claimed = returned_token is not None
        await self.session.commit()
        if claimed:
            self._remember_token(receipt.event_key, str(returned_token))
        return claimed

    async def mark_completed(self, event_key: str, *, commit: bool = True) -> None:
        """Complete only the lease generation still owned by this worker.

        A stale worker must not commit side effects after another worker has reclaimed
        the receipt. The fenced UPDATE is therefore treated as an ownership check: if
        it updates zero rows, the current transaction is rolled back and routing aborts.

        For commit=False callers, keep the task-local token until the caller's database
        commit succeeds. If that commit fails, release_failed() can still delete the
        original processing receipt so WAHA can retry instead of losing the command.
        """
        claim_token = self._token_for(event_key)
        if not claim_token:
            await self.session.rollback()
            raise InboundClaimLostError(f"inbound receipt lease missing for {event_key}")

        result = await self.session.execute(
            text(
                """
                UPDATE inbound_webhook_receipts
                SET status = 'completed', updated_at = NOW()
                WHERE event_key = :event_key
                  AND claim_token = :claim_token
                  AND status = 'processing'
                """
            ),
            {"event_key": event_key, "claim_token": claim_token},
        )
        if result.rowcount != 1:
            # This worker lost its generation lease. Roll back every side effect in the
            # same transaction before any caller can commit stale work.
            await self.session.rollback()
            self._forget_token(event_key, claim_token)
            raise InboundClaimLostError(f"inbound receipt lease lost for {event_key}")

        if not commit:
            # Do not forget yet: the caller still has to commit this transaction. A
            # commit failure must leave the token available to release_failed().
            return

        try:
            await self.session.commit()
        except Exception:
            # Keep the token so the caller can release the still-processing receipt if
            # the transaction did not commit.
            raise
        else:
            self._forget_token(event_key, claim_token)

    async def release_failed(self, event_key: str) -> None:
        """Release only this worker's failed claim so WAHA may safely retry."""
        claim_token = self._token_for(event_key)
        if claim_token:
            await self.session.execute(
                text(
                    """
                    DELETE FROM inbound_webhook_receipts
                    WHERE event_key = :event_key
                      AND claim_token = :claim_token
                      AND status = 'processing'
                    """
                ),
                {"event_key": event_key, "claim_token": claim_token},
            )
        await self.session.commit()
        self._forget_token(event_key, claim_token)

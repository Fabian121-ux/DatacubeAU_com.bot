from __future__ import annotations

import asyncio
import logging

from sqlalchemy import text

from app.db import SessionLocal
from app.services.deleted_message_service import DeletedMessageService
from app.services.logging_service import log_event


logger = logging.getLogger(__name__)


async def deleted_message_reconciliation_worker() -> None:
    """Durably reconcile unmatched revoke audits against messages committed later.

    The unmatched revoke is already durable PostgreSQL evidence. This worker closes races
    between independent webhook requests and survives process restarts; it does not create
    content for messages Zina never observed. A transient database/service failure must not
    permanently terminate this authoritative fallback while the API process keeps running.
    """
    while True:
        try:
            reconciled = await _reconcile_pending_batch(limit=50)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            log_event(
                logger,
                logging.ERROR,
                "message_revocation_reconciliation_iteration_failed",
                error_type=type(exc).__name__,
            )
            await asyncio.sleep(5)
            continue

        await asyncio.sleep(2 if reconciled else 5)


async def _reconcile_pending_batch(*, limit: int) -> int:
    async with SessionLocal() as db:
        # Only currently reconcilable audits may consume the bounded batch. A revoke for
        # content Zina never observed remains truthful unmatched evidence, but it cannot
        # permanently starve a later revoke whose Message has since committed.
        rows = (
            await db.execute(
                text(
                    """
                    SELECT
                        a.id,
                        a.details_json->>'revoked_message_id' AS source_message_id,
                        NULLIF(a.details_json->>'chat_id', '') AS chat_id
                    FROM audit_logs a
                    WHERE a.action = 'message_revocation_unmatched'
                      AND NULLIF(a.details_json->>'revoked_message_id', '') IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM audit_logs done
                          WHERE done.action = 'message_revocation_late_reconciled'
                            AND done.details_json->>'source_unmatched_audit_id' = a.id::text
                      )
                      AND EXISTS (
                          SELECT 1
                          FROM messages m
                          WHERE m.lifecycle_status <> 'revoked'
                            AND (
                                m.source_message_id = a.details_json->>'revoked_message_id'
                                OR m.raw_payload_json->>'id' = a.details_json->>'revoked_message_id'
                                OR m.raw_payload_json->'message'->>'id' = a.details_json->>'revoked_message_id'
                            )
                            AND (
                                NULLIF(a.details_json->>'chat_id', '') IS NULL
                                OR m.chat_id = a.details_json->>'chat_id'
                            )
                      )
                    ORDER BY a.created_at, a.id
                    LIMIT :limit
                    """
                ),
                {"limit": max(1, min(int(limit), 200))},
            )
        ).mappings().all()

        service = DeletedMessageService(db)
        reconciled = 0
        for row in rows:
            source_message_id = str(row.get("source_message_id") or "").strip()
            if not source_message_id:
                continue
            if await service.reconcile_pending_for_message(
                source_message_id=source_message_id,
                chat_id=str(row.get("chat_id") or "").strip() or None,
            ):
                reconciled += 1

        if reconciled:
            await db.commit()
            log_event(logger, logging.INFO, "message_revocation_batch_reconciled", count=reconciled)
        else:
            await db.rollback()
        return reconciled

BEGIN;

ALTER TABLE inbound_webhook_receipts
    ADD COLUMN IF NOT EXISTS claim_token VARCHAR(64);

-- Historical processing receipts predate generation fencing. They may be safely
-- reclaimed by a new worker after the normal lease; completed rows do not need a token.
CREATE INDEX IF NOT EXISTS idx_inbound_webhook_receipts_processing_claim
    ON inbound_webhook_receipts(event_key, claim_token)
    WHERE status = 'processing';

COMMIT;

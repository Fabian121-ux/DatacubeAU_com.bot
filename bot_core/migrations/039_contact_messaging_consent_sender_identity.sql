BEGIN;

-- Preserve sender identity separately from the exact transport chat alias. A pending
-- STOP can arrive on an unmapped WAHA/LID alias while its sender identity still maps
-- to an existing Contact; the final outbound fence uses this bounded identity set.
ALTER TABLE inbound_webhook_receipts
    ADD COLUMN IF NOT EXISTS sender_identity_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_inbound_webhook_receipts_pending_opt_out_sender_ids
    ON inbound_webhook_receipts USING GIN (sender_identity_ids)
    WHERE opt_out_intent IS TRUE AND status = 'processing';

COMMIT;

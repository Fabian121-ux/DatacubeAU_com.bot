BEGIN;

-- A pending STOP may arrive on an unmapped transport alias while its sender resolves
-- to a Contact whose aliases later change. Persist the resolved Contact IDs on the
-- durable receipt so the final worker veto does not depend on mutable current aliases.
ALTER TABLE inbound_webhook_receipts
    ADD COLUMN IF NOT EXISTS sender_contact_ids JSONB NOT NULL DEFAULT '[]'::jsonb;

CREATE INDEX IF NOT EXISTS ix_inbound_webhook_receipts_pending_opt_out_contacts
    ON inbound_webhook_receipts USING GIN (sender_contact_ids)
    WHERE opt_out_intent IS TRUE AND status = 'processing';

COMMIT;

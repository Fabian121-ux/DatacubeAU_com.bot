BEGIN;

CREATE TABLE IF NOT EXISTS contact_messaging_consents (
    id BIGSERIAL PRIMARY KEY,
    contact_id BIGINT NOT NULL REFERENCES contacts(id) ON DELETE CASCADE,
    exact_chat_id VARCHAR(120) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'unknown',
    provenance VARCHAR(40),
    evidence_ref VARCHAR(240),
    granted_by VARCHAR(120),
    granted_at TIMESTAMPTZ,
    expires_at TIMESTAMPTZ,
    opted_out_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_contact_messaging_consent_identity UNIQUE (contact_id, exact_chat_id),
    CONSTRAINT ck_contact_messaging_consent_status
        CHECK (status IN ('unknown', 'consented', 'opted_out', 'revoked'))
);

CREATE INDEX IF NOT EXISTS ix_contact_messaging_consent_dispatch
    ON contact_messaging_consents (exact_chat_id, status, expires_at);

CREATE TABLE IF NOT EXISTS contact_messaging_consent_events (
    id BIGSERIAL PRIMARY KEY,
    -- Historical IDs are intentionally not foreign keys: deleting live state must
    -- never rewrite the append-only audit history.
    consent_id BIGINT,
    contact_id BIGINT,
    exact_chat_id VARCHAR(120) NOT NULL,
    event_type VARCHAR(24) NOT NULL,
    actor_type VARCHAR(24) NOT NULL,
    actor_identity VARCHAR(120),
    evidence_ref VARCHAR(240),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_contact_messaging_consent_event_type
        CHECK (event_type IN ('granted', 'revoked', 'opted_out')),
    CONSTRAINT ck_contact_messaging_consent_event_actor
        CHECK (actor_type IN ('owner', 'contact', 'system'))
);

CREATE INDEX IF NOT EXISTS ix_contact_messaging_consent_events_identity
    ON contact_messaging_consent_events (contact_id, exact_chat_id, created_at DESC);

-- A claimed explicit opt-out must veto an outbound attempt even while routing waits
-- on the exact-chat mapping lock. The receipt is completed only after consent state
-- and its audit event have committed.
ALTER TABLE inbound_webhook_receipts
    ADD COLUMN IF NOT EXISTS opt_out_intent BOOLEAN NOT NULL DEFAULT FALSE;

CREATE INDEX IF NOT EXISTS ix_inbound_webhook_receipts_pending_opt_out
    ON inbound_webhook_receipts (chat_id, updated_at)
    WHERE opt_out_intent IS TRUE AND status = 'processing';

CREATE OR REPLACE FUNCTION prevent_contact_messaging_consent_event_mutation()
RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'contact_messaging_consent_events is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contact_messaging_consent_events_immutable
    ON contact_messaging_consent_events;
CREATE TRIGGER trg_contact_messaging_consent_events_immutable
    BEFORE UPDATE OR DELETE ON contact_messaging_consent_events
    FOR EACH ROW EXECUTE FUNCTION prevent_contact_messaging_consent_event_mutation();

-- Row-level triggers do not fire for TRUNCATE. Keep the audit table append-only
-- for ordinary SQL callers by rejecting that separate statement operation too.
DROP TRIGGER IF EXISTS trg_contact_messaging_consent_events_no_truncate
    ON contact_messaging_consent_events;
CREATE TRIGGER trg_contact_messaging_consent_events_no_truncate
    BEFORE TRUNCATE ON contact_messaging_consent_events
    FOR EACH STATEMENT EXECUTE FUNCTION prevent_contact_messaging_consent_event_mutation();


-- A terminal opt-out is bound to the durable Contact identity, not only the
-- current chat alias. Do not allow physical deletion/re-import to manufacture
-- a fresh Contact ID and bypass that immutable history. An explicit future
-- erasure workflow must anonymize the Contact while preserving this veto.
CREATE OR REPLACE FUNCTION prevent_contact_delete_after_terminal_opt_out()
RETURNS trigger AS $
BEGIN
    IF EXISTS (
        SELECT 1
        FROM contact_messaging_consent_events
        WHERE contact_id = OLD.id
          AND event_type = 'opted_out'
    ) THEN
        RAISE EXCEPTION
            'contact has terminal messaging opt-out; preserve identity continuity';
    END IF;
    RETURN OLD;
END;
$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contacts_preserve_terminal_messaging_opt_out ON contacts;
CREATE TRIGGER trg_contacts_preserve_terminal_messaging_opt_out
    BEFORE DELETE ON contacts
    FOR EACH ROW
    EXECUTE FUNCTION prevent_contact_delete_after_terminal_opt_out();

-- TRUNCATE bypasses row-level DELETE triggers, so preserve the same identity
-- invariant for bulk contact cleanup while any terminal opt-out history exists.
CREATE OR REPLACE FUNCTION prevent_contact_truncate_after_terminal_opt_out()
RETURNS trigger AS $
BEGIN
    IF EXISTS (
        SELECT 1
        FROM contact_messaging_consent_events
        WHERE event_type = 'opted_out'
    ) THEN
        RAISE EXCEPTION
            'contacts contain terminal messaging opt-out history; TRUNCATE is refused';
    END IF;
    RETURN NULL;
END;
$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_contacts_preserve_terminal_opt_out_no_truncate ON contacts;
CREATE TRIGGER trg_contacts_preserve_terminal_opt_out_no_truncate
    BEFORE TRUNCATE ON contacts
    FOR EACH STATEMENT
    EXECUTE FUNCTION prevent_contact_truncate_after_terminal_opt_out();

COMMIT;

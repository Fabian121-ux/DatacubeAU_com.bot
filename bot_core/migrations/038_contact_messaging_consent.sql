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
    consent_id BIGINT REFERENCES contact_messaging_consents(id) ON DELETE SET NULL,
    contact_id BIGINT REFERENCES contacts(id) ON DELETE SET NULL,
    exact_chat_id VARCHAR(120) NOT NULL,
    event_type VARCHAR(24) NOT NULL,
    actor_type VARCHAR(24) NOT NULL,
    actor_identity VARCHAR(120),
    evidence_ref VARCHAR(240),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_contact_messaging_consent_event_type
        CHECK (event_type IN ('granted', 'reconsented', 'revoked', 'opted_out')),
    CONSTRAINT ck_contact_messaging_consent_event_actor
        CHECK (actor_type IN ('owner', 'contact', 'system'))
);

CREATE INDEX IF NOT EXISTS ix_contact_messaging_consent_events_identity
    ON contact_messaging_consent_events (contact_id, exact_chat_id, created_at DESC);

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

COMMIT;

-- Capability-truthful view-once metadata only.
-- No media bytes or private WAHA media URLs are persisted by this migration.

CREATE TABLE IF NOT EXISTS view_once_media_metadata (
    id BIGSERIAL PRIMARY KEY,
    source_message_id VARCHAR(200) NOT NULL UNIQUE,
    source_chat_id VARCHAR(120) NOT NULL,
    source_contact_id BIGINT NULL REFERENCES contacts(id) ON DELETE SET NULL,
    media_type VARCHAR(40) NULL,
    media_mime VARCHAR(160) NULL,
    capability_state VARCHAR(40) NOT NULL,
    evidence_source VARCHAR(80) NOT NULL,
    transport_available BOOLEAN NOT NULL DEFAULT FALSE,
    retention_mode VARCHAR(24) NOT NULL DEFAULT 'none',
    first_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    returned_to_owner_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL,
    metadata_json JSONB NULL
);

CREATE INDEX IF NOT EXISTS ix_view_once_media_metadata_chat_observed
    ON view_once_media_metadata (source_chat_id, last_observed_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_view_once_media_metadata_state_observed
    ON view_once_media_metadata (capability_state, last_observed_at DESC)
    WHERE deleted_at IS NULL;

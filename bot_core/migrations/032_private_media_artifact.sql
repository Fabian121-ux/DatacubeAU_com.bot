-- Foundational metadata layer for the Private Media Artifact service (roadmap phase 5,
-- docs/VIEW_ONCE_MEDIA_PIPELINE.md). This migration adds PostgreSQL authoritative
-- metadata only: opaque artifact ID, exact source message/contact/chat identifiers,
-- media kind/MIME/size/hash, transport provenance, retention policy, and lifecycle
-- timestamps. It does NOT add a private byte store, and no producer or delivery path
-- is wired to this table by this migration. No media bytes, base64 payloads, or public
-- download URLs are stored here; `storage_locator` stays NULL until an actual private
-- byte-storage backend exists behind PrivateMediaArtifactService.

CREATE TABLE IF NOT EXISTS private_media_artifacts (
    id BIGSERIAL PRIMARY KEY,
    artifact_id VARCHAR(64) NOT NULL UNIQUE,
    source_message_id VARCHAR(200) NOT NULL,
    source_chat_id VARCHAR(120) NOT NULL,
    source_contact_id BIGINT NULL REFERENCES contacts(id) ON DELETE SET NULL,
    owner_admin_account_id BIGINT NULL REFERENCES admin_accounts(id) ON DELETE SET NULL,
    media_kind VARCHAR(40) NOT NULL,
    media_mime VARCHAR(160) NULL,
    byte_size BIGINT NULL,
    content_hash VARCHAR(128) NULL,
    storage_locator TEXT NULL,
    transport_provenance VARCHAR(80) NOT NULL,
    retention_policy VARCHAR(24) NOT NULL DEFAULT 'none',
    retention_expires_at TIMESTAMPTZ NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_observed_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    disabled_at TIMESTAMPTZ NULL,
    deleted_at TIMESTAMPTZ NULL,
    metadata_json JSONB NULL,

    CONSTRAINT ck_private_media_artifacts_byte_size_nonnegative
        CHECK (byte_size IS NULL OR byte_size >= 0)
);

CREATE INDEX IF NOT EXISTS ix_private_media_artifacts_owner_active
    ON private_media_artifacts (owner_admin_account_id, last_observed_at DESC)
    WHERE deleted_at IS NULL;

CREATE INDEX IF NOT EXISTS ix_private_media_artifacts_source
    ON private_media_artifacts (source_chat_id, source_message_id)
    WHERE deleted_at IS NULL;

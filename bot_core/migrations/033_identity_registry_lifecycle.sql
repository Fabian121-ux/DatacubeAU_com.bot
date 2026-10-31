-- Identity Registry lifecycle fields: provenance/source, a typed entity_type
-- (distinct from the existing free-text category), and a soft-delete tombstone.
-- Purely additive; no existing column changes, no data migration required.

ALTER TABLE identity_registry
    ADD COLUMN IF NOT EXISTS source VARCHAR(120) NULL,
    ADD COLUMN IF NOT EXISTS entity_type VARCHAR(40) NULL,
    ADD COLUMN IF NOT EXISTS deleted_at TIMESTAMPTZ NULL;

CREATE INDEX IF NOT EXISTS ix_identity_registry_entity_type
    ON identity_registry (entity_type)
    WHERE deleted_at IS NULL;

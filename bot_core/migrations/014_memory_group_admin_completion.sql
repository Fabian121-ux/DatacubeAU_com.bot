BEGIN;

ALTER TABLE user_memory
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_memory_enabled
    ON user_memory (is_enabled, contact_id);

ALTER TABLE user_memory_timeline
    ADD COLUMN IF NOT EXISTS memory_type VARCHAR(40) NOT NULL DEFAULT 'profile_fact',
    ADD COLUMN IF NOT EXISTS importance DOUBLE PRECISION NOT NULL DEFAULT 0.5,
    ADD COLUMN IF NOT EXISTS is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_user_memory_timeline_enabled_contact
    ON user_memory_timeline (contact_id, is_enabled, updated_at DESC);

ALTER TABLE group_configs
    ADD COLUMN IF NOT EXISTS display_name VARCHAR(220),
    ADD COLUMN IF NOT EXISTS created_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

CREATE INDEX IF NOT EXISTS idx_group_configs_enabled
    ON group_configs (is_enabled, updated_at DESC);

COMMIT;

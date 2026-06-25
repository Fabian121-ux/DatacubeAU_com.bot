BEGIN;

CREATE TABLE IF NOT EXISTS command_catalog (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(80) NOT NULL UNIQUE,
    trigger_syntax TEXT NOT NULL DEFAULT '',
    category VARCHAR(80) NOT NULL,
    description TEXT NOT NULL,
    example TEXT NOT NULL,
    permissions VARCHAR(40) NOT NULL DEFAULT 'user',
    handler_target VARCHAR(160) NOT NULL DEFAULT '',
    usage_count INTEGER NOT NULL DEFAULT 0,
    last_used_at TIMESTAMPTZ,
    is_enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE command_catalog
    ADD COLUMN IF NOT EXISTS trigger_syntax TEXT NOT NULL DEFAULT '';

ALTER TABLE command_catalog
    ADD COLUMN IF NOT EXISTS handler_target VARCHAR(160) NOT NULL DEFAULT '';

ALTER TABLE command_catalog
    ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0;

ALTER TABLE command_catalog
    ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

UPDATE command_catalog
SET trigger_syntax = name
WHERE COALESCE(trigger_syntax, '') = '';

UPDATE command_catalog
SET handler_target = CASE
    WHEN name IN ('/help', '/start', '/status', '/review', '/whoami') THEN 'user_command:' || name
    WHEN name = '/global' THEN 'memory:global_chat'
    WHEN name = '!ask' THEN 'ai:one_shot'
    WHEN name LIKE '!%' THEN 'internet_command:' || name
    WHEN name LIKE '/%' THEN 'owner_command:' || name
    ELSE 'command:' || name
END
WHERE COALESCE(handler_target, '') = '';

CREATE INDEX IF NOT EXISTS idx_command_catalog_usage
    ON command_catalog (usage_count DESC, last_used_at DESC);

CREATE INDEX IF NOT EXISTS idx_command_catalog_category_enabled
    ON command_catalog (category, is_enabled);

-- Preserve legacy rows for audit, but stop command and protected identity
-- phrases from executing through Reply Rules after Command Center and
-- Identity Registry own those responsibilities.
UPDATE reply_rules
SET is_enabled = FALSE,
    updated_at = NOW()
WHERE lower(trim(keyword)) IN (
    'help',
    '/help',
    'commands',
    'status',
    '/status',
    'ping',
    'start',
    '/start',
    'who are you',
    'what is your name',
    'what''s your name',
    'whats your name',
    'who is zina',
    'what is zina',
    'what is datacube au',
    'who is fabian'
);

COMMIT;

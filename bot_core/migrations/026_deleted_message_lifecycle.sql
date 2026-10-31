BEGIN;

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS source_message_id VARCHAR(160),
    ADD COLUMN IF NOT EXISTS lifecycle_status VARCHAR(32) NOT NULL DEFAULT 'active',
    ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS revoked_event_id VARCHAR(160),
    ADD COLUMN IF NOT EXISTS revoke_metadata_json JSONB;

UPDATE messages
SET source_message_id = NULLIF(raw_payload_json->>'id', '')
WHERE source_message_id IS NULL
  AND raw_payload_json IS NOT NULL
  AND jsonb_typeof(raw_payload_json::jsonb) = 'object';

CREATE INDEX IF NOT EXISTS idx_messages_source_message_id
    ON messages (source_message_id)
    WHERE source_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_revoked_recent
    ON messages (revoked_at DESC, id DESC)
    WHERE lifecycle_status = 'revoked';

INSERT INTO command_catalog (
    name, trigger_syntax, category, description, example, permissions,
    handler_target, usage_count, is_enabled, created_at, updated_at
)
VALUES (
    '/deleted-message', '.dm', 'Admin Commands',
    'Inspect bounded deleted-message evidence that Zina observed before WAHA revocation.',
    '@Zina .dm', 'owner', 'command_control:deleted_message', 0, TRUE, NOW(), NOW()
)
ON CONFLICT (name) DO UPDATE SET
    trigger_syntax = EXCLUDED.trigger_syntax,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    example = EXCLUDED.example,
    permissions = EXCLUDED.permissions,
    handler_target = EXCLUDED.handler_target,
    updated_at = NOW();

COMMIT;

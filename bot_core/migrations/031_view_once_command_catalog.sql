BEGIN;

INSERT INTO command_catalog (
    name, trigger_syntax, category, description, example, permissions,
    handler_target, usage_count, is_enabled, created_at, updated_at
)
VALUES (
    '/vvopen', '.vv', 'Admin Commands',
    'Open or inspect explicitly detected WAHA view-once media for Fabian''s private owner inbox.',
    'Reply to a view-once item, then send @Zina .vv',
    'owner', 'command_control:view_once', 0, TRUE, NOW(), NOW()
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

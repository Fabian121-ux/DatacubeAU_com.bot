BEGIN;

INSERT INTO command_catalog (
    name, trigger_syntax, category, description, example, permissions,
    handler_target, usage_count, is_enabled, created_at, updated_at
)
VALUES (
    '/push', '.push', 'Admin Commands',
    'Push the replied WhatsApp message into Fabian''s private Zina self-DM control inbox.',
    '@Zina .push', 'owner', 'command_control:push', 0, TRUE, NOW(), NOW()
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

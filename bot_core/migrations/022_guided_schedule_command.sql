BEGIN;

INSERT INTO command_catalog (
    name,
    trigger_syntax,
    category,
    description,
    example,
    permissions,
    handler_target,
    usage_count,
    is_enabled,
    created_at,
    updated_at
)
VALUES (
    '/schedule',
    '.sch',
    'Admin Commands',
    'Start a guided owner scheduling draft in the WhatsApp self-DM control inbox.',
    '@Zina .sch',
    'owner',
    'command_control:schedule',
    0,
    TRUE,
    NOW(),
    NOW()
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

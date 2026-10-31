BEGIN;

INSERT INTO command_catalog (
    name, trigger_syntax, category, description, example, permissions,
    handler_target, usage_count, is_enabled, created_at, updated_at
)
VALUES
    ('/commands', '.commands', 'Admin Commands', 'List commands visible to the current authority.', '@Zina .commands', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/cmdinfo', '.cmdinfo', 'Admin Commands', 'Inspect command metadata, authority, state, and handler.', '.cmdinfo .sch', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/cmdon', '.cmdon', 'Admin Commands', 'Enable a registered Command Center command.', '.cmdon /weather', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/cmdoff', '.cmdoff', 'Admin Commands', 'Disable a registered Command Center command.', '.cmdoff /weather', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/config', '.config', 'Admin Commands', 'Inspect or change allow-listed non-secret Zina runtime configuration.', '.config get auto_assist_inactivity_seconds', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/contacts', '.contacts', 'Admin Commands', 'Summarize or list known saved and unsaved WhatsApp people.', '.contacts saved 20', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/contact', '.contact', 'Admin Commands', 'Resolve and inspect one WhatsApp contact safely.', '.contact Amanda Christabel', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW()),
    ('/contactsync', '.contactsync', 'Admin Commands', 'Refresh saved WhatsApp contacts through the existing WAHA contact sync.', '.contactsync', 'owner', 'command_control:management', 0, TRUE, NOW(), NOW())
ON CONFLICT (name) DO UPDATE SET
    trigger_syntax = EXCLUDED.trigger_syntax,
    category = EXCLUDED.category,
    description = EXCLUDED.description,
    example = EXCLUDED.example,
    permissions = EXCLUDED.permissions,
    handler_target = EXCLUDED.handler_target,
    updated_at = NOW();

COMMIT;

BEGIN;

INSERT INTO contacts (whatsapp_id, display_name)
VALUES ('234000000000@c.us', 'Local DM Tester')
ON CONFLICT (whatsapp_id) DO NOTHING;

INSERT INTO dm_configs (contact_id, is_enabled, cooldown_seconds)
SELECT id, TRUE, 6
FROM contacts
WHERE whatsapp_id = '234000000000@c.us'
ON CONFLICT (contact_id) DO UPDATE
SET is_enabled = EXCLUDED.is_enabled,
    cooldown_seconds = EXCLUDED.cooldown_seconds,
    updated_at = NOW();

INSERT INTO group_configs (chat_id, reply_mode, is_enabled, cooldown_seconds)
VALUES ('120363000000000000@g.us', 'mention_only', TRUE, 45)
ON CONFLICT (chat_id) DO UPDATE
SET reply_mode = EXCLUDED.reply_mode,
    is_enabled = EXCLUDED.is_enabled,
    cooldown_seconds = EXCLUDED.cooldown_seconds,
    updated_at = NOW();

COMMIT;

BEGIN;

ALTER TABLE outbound_queue
  ADD COLUMN IF NOT EXISTS formatting_json JSONB;

INSERT INTO bot_config (config_key, config_value) VALUES
  ('whatsapp_message_format', 'automatic')
ON CONFLICT (config_key) DO NOTHING;

COMMIT;

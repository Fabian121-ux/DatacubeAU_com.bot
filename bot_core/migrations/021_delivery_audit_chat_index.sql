BEGIN;

CREATE INDEX IF NOT EXISTS idx_audit_logs_outbound_sent_chat_created
ON audit_logs ((details_json->>'chat_id'), created_at DESC, id DESC)
WHERE action = 'outbound_queue_sent'
  AND entity_type = 'outbound_queue';

COMMIT;

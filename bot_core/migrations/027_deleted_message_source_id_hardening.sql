BEGIN;

UPDATE messages
SET source_message_id = COALESCE(
    NULLIF(raw_payload_json->>'id', ''),
    NULLIF(raw_payload_json->'message'->>'id', '')
)
WHERE source_message_id IS NULL
  AND raw_payload_json IS NOT NULL
  AND jsonb_typeof(raw_payload_json::jsonb) = 'object';

CREATE OR REPLACE FUNCTION zina_populate_message_source_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.source_message_id IS NULL OR BTRIM(NEW.source_message_id) = '' THEN
        NEW.source_message_id := COALESCE(
            NULLIF(NEW.raw_payload_json->>'id', ''),
            NULLIF(NEW.raw_payload_json->'message'->>'id', '')
        );
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_messages_source_message_id ON messages;
CREATE TRIGGER trg_messages_source_message_id
BEFORE INSERT OR UPDATE OF raw_payload_json, source_message_id ON messages
FOR EACH ROW
EXECUTE FUNCTION zina_populate_message_source_id();

CREATE INDEX IF NOT EXISTS idx_messages_raw_top_message_id
    ON messages ((raw_payload_json->>'id'))
    WHERE raw_payload_json->>'id' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_raw_nested_message_id
    ON messages ((raw_payload_json->'message'->>'id'))
    WHERE raw_payload_json->'message'->>'id' IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_unmatched_message_revocations
    ON audit_logs ((details_json->>'revoked_message_id'), created_at, id)
    WHERE action = 'message_revocation_unmatched';

COMMIT;

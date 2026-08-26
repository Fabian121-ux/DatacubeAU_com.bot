BEGIN;

CREATE OR REPLACE FUNCTION zina_resolve_message_source_id(payload jsonb)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    candidate jsonb;
    resolved text;
BEGIN
    IF payload IS NULL OR jsonb_typeof(payload) <> 'object' THEN
        RETURN NULL;
    END IF;

    candidate := payload->'id';
    IF candidate IS NULL AND jsonb_typeof(payload->'message') = 'object' THEN
        candidate := payload->'message'->'id';
    END IF;

    IF candidate IS NULL THEN
        RETURN NULL;
    END IF;

    CASE jsonb_typeof(candidate)
        WHEN 'string' THEN
            resolved := candidate #>> '{}';
        WHEN 'number' THEN
            resolved := candidate #>> '{}';
        WHEN 'object' THEN
            resolved := COALESCE(
                NULLIF(candidate->>'_serialized', ''),
                NULLIF(candidate->>'id', '')
            );
        ELSE
            resolved := NULL;
    END CASE;

    resolved := NULLIF(BTRIM(COALESCE(resolved, '')), '');
    IF resolved IS NULL OR LENGTH(resolved) > 160 THEN
        RETURN NULL;
    END IF;
    RETURN resolved;
END;
$$;

UPDATE messages
SET source_message_id = zina_resolve_message_source_id(raw_payload_json::jsonb)
WHERE raw_payload_json IS NOT NULL
  AND jsonb_typeof(raw_payload_json::jsonb) = 'object'
  AND zina_resolve_message_source_id(raw_payload_json::jsonb) IS NOT NULL
  AND (
      source_message_id IS NULL
      OR BTRIM(source_message_id) = ''
      OR source_message_id LIKE '{%'
  );

CREATE OR REPLACE FUNCTION zina_populate_message_source_id()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.source_message_id IS NULL OR BTRIM(NEW.source_message_id) = '' THEN
        NEW.source_message_id := zina_resolve_message_source_id(NEW.raw_payload_json::jsonb);
    END IF;
    RETURN NEW;
END;
$$;

COMMIT;

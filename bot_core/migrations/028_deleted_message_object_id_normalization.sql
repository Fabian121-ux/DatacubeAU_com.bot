BEGIN;

CREATE OR REPLACE FUNCTION zina_resolve_message_source_id(payload jsonb)
RETURNS text
LANGUAGE plpgsql
IMMUTABLE
AS $$
DECLARE
    candidate jsonb;
    resolved text;
    attempt integer;
BEGIN
    IF payload IS NULL OR jsonb_typeof(payload) <> 'object' THEN
        RETURN NULL;
    END IF;

    FOR attempt IN 1..2 LOOP
        IF attempt = 1 THEN
            candidate := payload->'id';
        ELSIF jsonb_typeof(payload->'message') = 'object' THEN
            candidate := payload->'message'->'id';
        ELSE
            candidate := NULL;
        END IF;

        resolved := NULL;
        IF candidate IS NOT NULL THEN
            CASE jsonb_typeof(candidate)
                WHEN 'string' THEN
                    resolved := candidate #>> '{}';
                WHEN 'number' THEN
                    resolved := candidate #>> '{}';
                WHEN 'object' THEN
                    IF jsonb_typeof(candidate->'_serialized') IN ('string', 'number') THEN
                        resolved := candidate->>'_serialized';
                    ELSIF jsonb_typeof(candidate->'id') IN ('string', 'number') THEN
                        resolved := candidate->>'id';
                    END IF;
                ELSE
                    resolved := NULL;
            END CASE;
        END IF;

        resolved := NULLIF(BTRIM(COALESCE(resolved, '')), '');
        IF resolved IS NOT NULL AND LENGTH(resolved) <= 160 THEN
            RETURN resolved;
        END IF;
    END LOOP;

    RETURN NULL;
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

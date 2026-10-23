-- Permanently reserve outbound message-set identifiers across physical deletion.
-- Migration 036 keeps a UNIQUE constraint on outbound_message_sets.set_key and usage
-- snapshots preserve the selected IDs, but a hard delete removes that unique-key row.
-- This registry keeps the identifier reserved after the set row and its variants are
-- physically removed. It is an audit-integrity primitive only; it grants no send authority.

CREATE TABLE IF NOT EXISTS outbound_message_set_keys (
    set_key VARCHAR(120) PRIMARY KEY,
    reserved_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    retired_at TIMESTAMPTZ NULL
);

-- Backfill both active and soft-deleted rows before enforcing the FK. A previously
-- deleted set starts retired; an active set remains reserved but not retired.
INSERT INTO outbound_message_set_keys (set_key, reserved_at, retired_at)
SELECT set_key, created_at, deleted_at
FROM outbound_message_sets
ON CONFLICT (set_key) DO UPDATE
SET reserved_at = LEAST(outbound_message_set_keys.reserved_at, EXCLUDED.reserved_at),
    retired_at = COALESCE(outbound_message_set_keys.retired_at, EXCLUDED.retired_at);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_outbound_message_sets_set_key_registry'
          AND conrelid = 'public.outbound_message_sets'::regclass
    ) THEN
        ALTER TABLE outbound_message_sets
            ADD CONSTRAINT fk_outbound_message_sets_set_key_registry
            FOREIGN KEY (set_key)
            REFERENCES outbound_message_set_keys (set_key)
            ON DELETE RESTRICT;
    END IF;
END;
$$;

CREATE OR REPLACE FUNCTION zina_reserve_outbound_message_set_key()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM outbound_message_set_keys WHERE set_key = NEW.set_key
    ) THEN
        RAISE EXCEPTION 'outbound message set key % has already been reserved', NEW.set_key
            USING ERRCODE = '23505', CONSTRAINT = 'outbound_message_set_keys_pkey';
    END IF;
    INSERT INTO outbound_message_set_keys (set_key) VALUES (NEW.set_key);
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_outbound_message_sets_reserve_key ON outbound_message_sets;
CREATE TRIGGER trg_outbound_message_sets_reserve_key
BEFORE INSERT ON outbound_message_sets
FOR EACH ROW
EXECUTE FUNCTION zina_reserve_outbound_message_set_key();

CREATE OR REPLACE FUNCTION zina_forbid_outbound_message_set_key_change()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    IF NEW.set_key IS DISTINCT FROM OLD.set_key THEN
        RAISE EXCEPTION
            'outbound message set_key is immutable; create a new set with a new key'
            USING ERRCODE = '23514';
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_outbound_message_sets_immutable_key ON outbound_message_sets;
CREATE TRIGGER trg_outbound_message_sets_immutable_key
BEFORE UPDATE OF set_key ON outbound_message_sets
FOR EACH ROW
EXECUTE FUNCTION zina_forbid_outbound_message_set_key_change();

CREATE OR REPLACE FUNCTION zina_retire_outbound_message_set_key()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    UPDATE outbound_message_set_keys
    SET retired_at = COALESCE(retired_at, NOW())
    WHERE set_key = OLD.set_key;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'missing reservation for outbound message set key %', OLD.set_key
            USING ERRCODE = '23503';
    END IF;
    RETURN OLD;
END;
$$;

DROP TRIGGER IF EXISTS trg_outbound_message_sets_retire_key ON outbound_message_sets;
CREATE TRIGGER trg_outbound_message_sets_retire_key
AFTER DELETE ON outbound_message_sets
FOR EACH ROW
EXECUTE FUNCTION zina_retire_outbound_message_set_key();

CREATE OR REPLACE FUNCTION zina_forbid_outbound_message_set_key_registry_delete()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
    RAISE EXCEPTION
        'outbound message set key reservations are permanent'
        USING ERRCODE = '23514';
END;
$$;

DROP TRIGGER IF EXISTS trg_outbound_message_set_key_registry_no_delete ON outbound_message_set_keys;
CREATE TRIGGER trg_outbound_message_set_key_registry_no_delete
BEFORE DELETE ON outbound_message_set_keys
FOR EACH ROW
EXECUTE FUNCTION zina_forbid_outbound_message_set_key_registry_delete();

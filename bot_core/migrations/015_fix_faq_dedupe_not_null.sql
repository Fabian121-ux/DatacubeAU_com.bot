BEGIN;

-- Give any legacy FAQ row without a key a safe, unique temporary key.
UPDATE faq_entries
SET dedupe_key = 'legacy-faq-' || id::text
WHERE dedupe_key IS NULL
   OR BTRIM(dedupe_key) = '';

-- Match the application schema requirement.
ALTER TABLE faq_entries
ALTER COLUMN dedupe_key SET NOT NULL;

COMMIT;

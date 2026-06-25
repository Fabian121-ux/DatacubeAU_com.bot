BEGIN;

-- P0.2: reply_rules must be idempotent across seeds, admin saves, and owner commands.
WITH ranked_reply_rules AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY
        NULLIF(
          BTRIM(
            REGEXP_REPLACE(
              REGEXP_REPLACE(LOWER(keyword), '[^[:alnum:]_[:space:]]+', ' ', 'g'),
              '[[:space:]]+',
              ' ',
              'g'
            )
          ),
          ''
        ),
        match_mode,
        COALESCE(chat_type_filter, 'all')
      ORDER BY priority DESC, updated_at DESC, id ASC
    ) AS rn
  FROM reply_rules
)
DELETE FROM reply_rules
USING ranked_reply_rules
WHERE reply_rules.id = ranked_reply_rules.id
  AND ranked_reply_rules.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_reply_rules_normalized_key_mode_chat
  ON reply_rules (
    NULLIF(
      BTRIM(
        REGEXP_REPLACE(
          REGEXP_REPLACE(LOWER(keyword), '[^[:alnum:]_[:space:]]+', ' ', 'g'),
          '[[:space:]]+',
          ' ',
          'g'
        )
      ),
      ''
    ),
    match_mode,
    COALESCE(chat_type_filter, 'all')
  );

-- P0.3: repeated imports should not queue identical pending candidates.
DO $$
BEGIN
  IF to_regclass('public.faq_import_candidates') IS NOT NULL THEN
    WITH ranked_faq_candidates AS (
      SELECT
        id,
        ROW_NUMBER() OVER (
          PARTITION BY normalized_question, MD5(answer)
          ORDER BY updated_at DESC, id ASC
        ) AS rn
      FROM faq_import_candidates
      WHERE status IN ('pending', 'duplicate')
    )
    DELETE FROM faq_import_candidates
    USING ranked_faq_candidates
    WHERE faq_import_candidates.id = ranked_faq_candidates.id
      AND ranked_faq_candidates.rn > 1;

    CREATE UNIQUE INDEX IF NOT EXISTS uq_faq_import_candidates_open_question_answer
      ON faq_import_candidates (normalized_question, MD5(answer))
      WHERE status IN ('pending', 'duplicate');
  END IF;
END $$;

COMMIT;

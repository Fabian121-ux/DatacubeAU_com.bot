BEGIN;

ALTER TABLE faq_entries
  ADD COLUMN IF NOT EXISTS category VARCHAR(80) NOT NULL DEFAULT 'General',
  ADD COLUMN IF NOT EXISTS intent VARCHAR(120) NOT NULL DEFAULT 'custom',
  ADD COLUMN IF NOT EXISTS dedupe_key TEXT NOT NULL DEFAULT '',
  ADD COLUMN IF NOT EXISTS question_variations JSON,
  ADD COLUMN IF NOT EXISTS keywords JSON,
  ADD COLUMN IF NOT EXISTS entities JSON,
  ADD COLUMN IF NOT EXISTS confidence_threshold DOUBLE PRECISION NOT NULL DEFAULT 0.72,
  ADD COLUMN IF NOT EXISTS usage_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS success_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS failed_count INTEGER NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS last_used_at TIMESTAMPTZ;

CREATE INDEX IF NOT EXISTS idx_faq_entries_category_enabled ON faq_entries (category, is_enabled);
CREATE INDEX IF NOT EXISTS idx_faq_entries_intent_enabled ON faq_entries (intent, is_enabled);

UPDATE faq_entries
SET
  category = 'Commands',
  intent = 'command_help',
  dedupe_key = 'intent:command_help'
WHERE LOWER(TRIM(question)) IN ('help', '/help', 'commands')
   OR normalized_question IN ('help', 'commands');

UPDATE faq_entries
SET dedupe_key = normalized_question
WHERE COALESCE(dedupe_key, '') = '';

WITH ranked AS (
  SELECT
    id,
    ROW_NUMBER() OVER (
      PARTITION BY dedupe_key
      ORDER BY usage_count DESC, success_count DESC, updated_at DESC, id ASC
    ) AS rn
  FROM faq_entries
)
DELETE FROM faq_entries
USING ranked
WHERE faq_entries.id = ranked.id
  AND ranked.rn > 1;

CREATE UNIQUE INDEX IF NOT EXISTS uq_faq_entries_dedupe_key ON faq_entries (dedupe_key);

CREATE TABLE IF NOT EXISTS faq_import_candidates (
  id                    BIGSERIAL PRIMARY KEY,
  source_name           VARCHAR(220),
  source_text           TEXT,
  category              VARCHAR(80) NOT NULL DEFAULT 'General',
  intent                VARCHAR(120) NOT NULL DEFAULT 'custom',
  question              TEXT NOT NULL,
  normalized_question   TEXT NOT NULL,
  question_variations   JSON,
  keywords              JSON,
  entities              JSON,
  answer                TEXT NOT NULL,
  confidence_score      DOUBLE PRECISION NOT NULL DEFAULT 0.0,
  duplicate_of_faq_id   BIGINT REFERENCES faq_entries(id) ON DELETE SET NULL,
  status                VARCHAR(30) NOT NULL DEFAULT 'pending',
  created_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at            TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  reviewed_at           TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_faq_import_candidates_status ON faq_import_candidates (status, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_faq_import_candidates_normalized ON faq_import_candidates (normalized_question);

CREATE TABLE IF NOT EXISTS identity_registry (
  id           BIGSERIAL PRIMARY KEY,
  registry_key VARCHAR(120) NOT NULL UNIQUE,
  category     VARCHAR(80) NOT NULL DEFAULT 'Identity',
  name         VARCHAR(180) NOT NULL,
  description  TEXT NOT NULL,
  aliases      JSON,
  keywords     JSON,
  entities     JSON,
  answer       TEXT NOT NULL,
  facts_json   JSON,
  is_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_identity_registry_category_enabled ON identity_registry (category, is_enabled);

CREATE TABLE IF NOT EXISTS command_catalog (
  id           BIGSERIAL PRIMARY KEY,
  name         VARCHAR(80) NOT NULL UNIQUE,
  category     VARCHAR(80) NOT NULL,
  description  TEXT NOT NULL,
  example      TEXT NOT NULL,
  permissions  VARCHAR(40) NOT NULL DEFAULT 'user',
  is_enabled   BOOLEAN NOT NULL DEFAULT TRUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_command_catalog_category_enabled ON command_catalog (category, is_enabled);

INSERT INTO identity_registry
  (registry_key, category, name, description, aliases, keywords, entities, answer, facts_json)
VALUES
  (
    'zina',
    'Zina',
    'Zina',
    'Fabian''s personal AI assistant inside WhatsApp.',
    '["Zina", "assistant", "you"]',
    '["assistant", "name", "created", "built", "owner"]',
    '["Zina", "Fabian"]',
    'I am Zina, Fabian''s AI assistant.',
    '{"owner": "Fabian", "type": "AI assistant"}'
  ),
  (
    'fabian',
    'Owner',
    'Fabian',
    'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.',
    '["Fabian", "owner", "creator"]',
    '["owner", "creator", "developer", "builder"]',
    '["Fabian"]',
    'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.',
    '{"role": "Owner and creator"}'
  ),
  (
    'datacube_au',
    'Datacube AU',
    'Datacube AU',
    'An AI-powered educational intelligence platform focused on document intelligence, exam preparation, knowledge retrieval, and personalized learning.',
    '["Datacube AU", "Datacube", "it"]',
    '["datacube", "owner", "founder", "project", "education", "learning"]',
    '["Datacube AU", "Fabian"]',
    'Datacube AU is an AI-powered educational intelligence platform founded by Fabian.',
    '{"owner": "Fabian", "project": true}'
  ),
  (
    'zinax',
    'ZinaX',
    'ZinaX',
    'A project in Fabian''s AI assistant and automation ecosystem.',
    '["ZinaX"]',
    '["zinax", "project", "assistant", "automation"]',
    '["ZinaX", "Fabian"]',
    'ZinaX is a project in Fabian''s AI assistant and automation ecosystem.',
    '{"owner": "Fabian", "project": true}'
  ),
  (
    'projects',
    'Projects',
    'Fabian Projects',
    'Fabian''s core projects include Datacube AU, Zina, ZinaX, and Moxiz Gateway.',
    '["Fabian projects", "projects"]',
    '["projects", "datacube", "zina", "zinax", "moxiz"]',
    '["Fabian", "Datacube AU", "Zina", "ZinaX", "Moxiz Gateway"]',
    'Fabian''s core projects are Datacube AU, Zina, ZinaX, and Moxiz Gateway.',
    '{"projects": ["Datacube AU", "Zina", "ZinaX", "Moxiz Gateway"]}'
  ),
  (
    'services',
    'Services',
    'Fabian Services',
    'Fabian builds AI-assisted systems, automation tools, and productivity-focused projects.',
    '["services", "what Fabian offers"]',
    '["services", "automation", "ai", "systems", "productivity"]',
    '["Fabian", "Datacube AU", "Zina"]',
    'Fabian focuses on AI-assisted systems, automation tools, WhatsApp assistant systems, and productivity-focused projects.',
    '{"services": ["AI-assisted systems", "Automation tools", "WhatsApp assistant systems", "Productivity projects"]}'
  )
ON CONFLICT (registry_key) DO NOTHING;

INSERT INTO command_catalog (name, category, description, example, permissions) VALUES
  ('/help', 'User Commands', 'Show available user commands.', '/help', 'user'),
  ('/status', 'User Commands', 'Check bot availability and basic status.', '/status', 'user'),
  ('/whoami', 'User Commands', 'Show the sender identity keys and owner-command permission status.', '/whoami', 'user'),
  ('/owner-help', 'Owner Commands', 'Show owner-only command help.', '/owner-help', 'owner'),
  ('/faq-import', 'Owner Commands', 'Import plain text or Markdown into the FAQ candidate queue for review.', '/faq-import\nWho is Fabian?\n\nFabian is an AI systems builder.', 'owner'),
  ('/teach', 'Owner Commands', 'Create or update one approved FAQ entry from a labeled question and answer.', '/teach\nQuestion:\nWhat is Zina?\n\nAnswer:\nZina is Fabian''s AI assistant.', 'owner'),
  ('/create-command', 'Owner Commands', 'Create a custom slash command reply.', '/create-command\nCommand:\n/scholarship\nReply:\nCheck School Info updates.', 'owner'),
  ('/edit-command', 'Owner Commands', 'Edit a custom slash command reply.', '/edit-command\nCommand:\n/scholarship\nReply:\nUpdated reply.', 'owner'),
  ('/delete-command', 'Owner Commands', 'Delete a custom slash command reply.', '/delete-command /scholarship', 'owner'),
  ('/internet', 'Owner Commands', 'Enable or disable internet services.', '/internet on', 'owner'),
  ('/web', 'Owner Commands', 'Enable or disable web search.', '/web on', 'owner'),
  ('/internet-status', 'Owner Commands', 'Show internet service status.', '/internet-status', 'owner'),
  ('!search', 'Internet Commands', 'Run a web search when internet access is enabled.', '!search latest AI news', 'user'),
  ('!news', 'Internet Commands', 'Search recent news when internet access is enabled.', '!news artificial intelligence', 'user'),
  ('!weather', 'Internet Commands', 'Search weather information when internet access is enabled.', '!weather Lagos', 'user'),
  ('!currency', 'Internet Commands', 'Convert or search currency rates when enabled.', '!currency 100 USD to NGN', 'user'),
  ('!image', 'Media Commands', 'Search images when enabled.', '!image Datacube AU', 'user'),
  ('!gif', 'Media Commands', 'Search GIFs when enabled.', '!gif celebration', 'user'),
  ('/remember', 'Memory Commands', 'Store an owner-provided memory fact.', '/remember Fabian prefers concise replies.', 'owner'),
  ('/memory-search', 'Memory Commands', 'Search saved memory.', '/memory-search Datacube', 'owner'),
  ('/enable-ai', 'Owner Commands', 'Enable AI fallback.', '/enable-ai', 'owner'),
  ('/disable-ai', 'Owner Commands', 'Disable AI fallback.', '/disable-ai', 'owner')
ON CONFLICT (name) DO NOTHING;

UPDATE command_catalog
SET category = 'Owner Commands', updated_at = NOW()
WHERE name IN ('/enable-ai', '/disable-ai')
  AND category = 'Experimental Commands';

COMMIT;

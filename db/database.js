'use strict';

require('dotenv').config();
const initSqlJs = require('sql.js');
const path = require('path');
const fs = require('fs');
const logger = require('../utils/logger');

const DB_PATH = process.env.DB_PATH || './data/datacube.db';

// Ensure data directory exists
const dbDir = path.dirname(path.resolve(DB_PATH));
if (!fs.existsSync(dbDir)) {
  fs.mkdirSync(dbDir, { recursive: true });
}

let db = null;
let SQL = null;

// Initialize sql.js and load database
async function initSql() {
  if (SQL) return SQL;
  
  SQL = await initSqlJs();
  return SQL;
}

// Load existing database or create new one
async function loadDb() {
  const SQL = await initSql();
  
  const dbPath = path.resolve(DB_PATH);
  
  if (fs.existsSync(dbPath)) {
    const fileBuffer = fs.readFileSync(dbPath);
    db = new SQL.Database(fileBuffer);
    logger.info('Loaded existing database from', DB_PATH);
  } else {
    db = new SQL.Database();
    logger.info('Created new database at', DB_PATH);
  }
  
  return db;
}

// Get database instance (creates if needed)
async function getDb() {
  if (!db) {
    await loadDb();
  }
  return db;
}

// Save database to disk
function saveDb() {
  if (db) {
    const data = db.export();
    const buffer = Buffer.from(data);
    fs.writeFileSync(path.resolve(DB_PATH), buffer);
  }
}

// Wrapper to make queries synchronous-like
function run(sql, params = []) {
  db.run(sql, params);
  saveDb();
}

function exec(sql) {
  db.exec(sql);
  saveDb();
}

function get(sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  if (stmt.step()) {
    const row = stmt.getAsObject();
    stmt.free();
    return row;
  }
  stmt.free();
  return null;
}

function all(sql, params = []) {
  const stmt = db.prepare(sql);
  stmt.bind(params);
  const rows = [];
  while (stmt.step()) {
    rows.push(stmt.getAsObject());
  }
  stmt.free();
  return rows;
}

async function initSchema() {
  const database = await getDb();

  database.exec(`
    -- users table
    CREATE TABLE IF NOT EXISTS users (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jid TEXT UNIQUE NOT NULL,
      name TEXT,
      opted_in INTEGER DEFAULT 0,
      first_seen TEXT NOT NULL,
      last_seen TEXT NOT NULL,
      message_count INTEGER DEFAULT 0,
      ai_call_count INTEGER DEFAULT 0
    );

    -- messages table (preview only — no full private logs)
    CREATE TABLE IF NOT EXISTS bot_numbers (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      phone TEXT NOT NULL UNIQUE,
      label TEXT,
      status TEXT NOT NULL DEFAULT 'idle', -- idle | pairing | connected | disconnected
      last_connected_at INTEGER,
      created_at INTEGER NOT NULL
    );

    CREATE TABLE IF NOT EXISTS messages (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jid TEXT NOT NULL,
      preview TEXT,
      ts INTEGER,
      used_ai INTEGER DEFAULT 0,
      number_id INTEGER,
      direction TEXT NOT NULL,       -- 'in' | 'out'
      content_preview TEXT,          -- first 100 chars only
      handler TEXT,                  -- 'rule:help' | 'ai' | 'onboard' | 'ratelimit'
      timestamp TEXT NOT NULL
    );

    -- ai_calls table
    CREATE TABLE IF NOT EXISTS ai_calls (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jid TEXT NOT NULL,
      model TEXT NOT NULL,
      prompt_tokens INTEGER,
      completion_tokens INTEGER,
      cost_usd REAL,
      success INTEGER DEFAULT 1,
      timestamp TEXT NOT NULL
    );

    -- rate_limits table
    CREATE TABLE IF NOT EXISTS rate_limits (
      jid TEXT PRIMARY KEY,
      ai_calls_this_hour INTEGER DEFAULT 0,
      window_start TEXT NOT NULL,
      total_messages_today INTEGER DEFAULT 0,
      day_start TEXT NOT NULL
    );

    -- QA cache table for fast repeated answers
    CREATE TABLE IF NOT EXISTS qa_cache (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      normalized_question TEXT NOT NULL UNIQUE,
      embedding_hash_or_fingerprint TEXT,
      answer_text TEXT NOT NULL,
      source TEXT NOT NULL,         -- 'ai' | 'faq'
      model TEXT,
      created_at TEXT NOT NULL,
      last_used_at TEXT NOT NULL,
      hit_count INTEGER DEFAULT 0,
      expires_at TEXT
    );

    -- Message-level trend metrics (sanitized metadata only)
    CREATE TABLE IF NOT EXISTS trend_events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jid_hash TEXT,
      category TEXT NOT NULL,       -- STATIC_COMMAND | FAQ_MATCH | CACHED_ANSWER | AI_REQUIRED | HUMAN_HANDOFF
      topic TEXT,
      was_ai_used INTEGER DEFAULT 0,
      cache_hit INTEGER DEFAULT 0,
      ai_cost_usd REAL DEFAULT 0,
      timestamp TEXT NOT NULL
    );

    -- Unified operational events/audit log
    CREATE TABLE IF NOT EXISTS events (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      message_id TEXT,
      jid_hash TEXT,
      event_type TEXT NOT NULL,
      stage TEXT NOT NULL,
      intent TEXT,
      route_category TEXT,
      topic TEXT,
      detail TEXT,
      success INTEGER DEFAULT 1,
      cache_hit INTEGER DEFAULT 0,
      ai_cost_usd REAL DEFAULT 0,
      created_at TEXT NOT NULL
    );

    -- Daily aggregated counters for trend reporting
    CREATE TABLE IF NOT EXISTS trends_daily (
      day TEXT PRIMARY KEY,
      total_messages INTEGER DEFAULT 0,
      ai_calls INTEGER DEFAULT 0,
      cache_hits INTEGER DEFAULT 0,
      ai_cost_usd REAL DEFAULT 0,
      updated_at TEXT NOT NULL
    );

    -- Admin managed custom commands
    CREATE TABLE IF NOT EXISTS commands (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL UNIQUE,
      description TEXT,
      response TEXT,
      response_text TEXT NOT NULL,
      use_ai INTEGER DEFAULT 0,
      tags TEXT,
      enabled INTEGER DEFAULT 1,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- Uploaded knowledge base documents
    CREATE TABLE IF NOT EXISTS kb_documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      title TEXT NOT NULL,
      source_type TEXT NOT NULL,
      content TEXT NOT NULL,
      fingerprint TEXT NOT NULL,
      tags TEXT,
      status TEXT NOT NULL DEFAULT 'active',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- Chunked KB segments for retrieval
    CREATE TABLE IF NOT EXISTS kb_chunks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      document_id INTEGER NOT NULL,
      chunk_index INTEGER NOT NULL,
      chunk_text TEXT NOT NULL,
      fingerprint TEXT NOT NULL,
      keywords TEXT,
      created_at TEXT NOT NULL,
      UNIQUE(document_id, chunk_index),
      FOREIGN KEY (document_id) REFERENCES kb_documents(id) ON DELETE CASCADE
    );

    -- Outbound delivery queue (persistent with retries)
    CREATE TABLE IF NOT EXISTS message_queue (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      jid TEXT NOT NULL,
      number_id INTEGER,
      payload_json TEXT NOT NULL,
      source TEXT,
      status TEXT NOT NULL DEFAULT 'queued', -- queued | sending | sent | retry | dead_letter
      attempt_count INTEGER DEFAULT 0,
      max_attempts INTEGER DEFAULT 5,
      next_attempt_at TEXT NOT NULL,
      last_error TEXT,
      dead_letter INTEGER DEFAULT 0,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      sent_at TEXT
    );

    -- Idempotency guard for inbound WhatsApp messages
    CREATE TABLE IF NOT EXISTS processed_messages (
      message_id TEXT PRIMARY KEY,
      jid TEXT NOT NULL,
      route_category TEXT,
      processed_at TEXT NOT NULL
    );

    -- config table
    CREATE TABLE IF NOT EXISTS config (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    -- Indexes for performance
    CREATE INDEX IF NOT EXISTS idx_bot_numbers_phone ON bot_numbers(phone);
    CREATE INDEX IF NOT EXISTS idx_bot_numbers_status ON bot_numbers(status);
    CREATE INDEX IF NOT EXISTS idx_messages_jid ON messages(jid);
    CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages(timestamp);
    CREATE INDEX IF NOT EXISTS idx_ai_calls_jid ON ai_calls(jid);
    CREATE INDEX IF NOT EXISTS idx_ai_calls_timestamp ON ai_calls(timestamp);
    CREATE INDEX IF NOT EXISTS idx_qa_cache_norm ON qa_cache(normalized_question);
    CREATE INDEX IF NOT EXISTS idx_qa_cache_expires ON qa_cache(expires_at);
    CREATE INDEX IF NOT EXISTS idx_trend_events_ts ON trend_events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_trend_events_topic ON trend_events(topic);
    CREATE INDEX IF NOT EXISTS idx_trend_events_category ON trend_events(category);
    CREATE INDEX IF NOT EXISTS idx_events_created_at ON events(created_at);
    CREATE INDEX IF NOT EXISTS idx_events_category ON events(route_category);
    CREATE INDEX IF NOT EXISTS idx_events_intent ON events(intent);
    CREATE INDEX IF NOT EXISTS idx_kb_documents_status ON kb_documents(status);
    CREATE INDEX IF NOT EXISTS idx_kb_chunks_document ON kb_chunks(document_id);
    CREATE INDEX IF NOT EXISTS idx_message_queue_status_next ON message_queue(status, next_attempt_at);
    CREATE INDEX IF NOT EXISTS idx_processed_messages_processed_at ON processed_messages(processed_at);
  `);

  function hasColumn(tableName, columnName) {
    const columns = all(`PRAGMA table_info(${tableName})`);
    return columns.some((column) => column.name === columnName);
  }

  function ensureColumn(tableName, definition) {
    const columnName = definition.split(/\s+/)[0];
    if (hasColumn(tableName, columnName)) return;
    exec(`ALTER TABLE ${tableName} ADD COLUMN ${definition}`);
  }

  // Backward-compatible schema upgrades for existing DB files.
  ensureColumn('messages', 'preview TEXT');
  ensureColumn('messages', 'ts INTEGER');
  ensureColumn('messages', 'used_ai INTEGER DEFAULT 0');
  ensureColumn('messages', 'number_id INTEGER');
  ensureColumn('commands', 'response TEXT');
  ensureColumn('processed_messages', 'number_id INTEGER');
  ensureColumn('message_queue', 'number_id INTEGER');

  // Create indexes only after migration columns are guaranteed to exist.
  exec('CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(ts)');
  exec('CREATE INDEX IF NOT EXISTS idx_messages_number_id ON messages(number_id)');
  exec('CREATE INDEX IF NOT EXISTS idx_message_queue_number_id ON message_queue(number_id)');

  run(
    `
    UPDATE messages
    SET preview = COALESCE(preview, content_preview),
        ts = COALESCE(ts, CAST(strftime('%s', timestamp) AS INTEGER) * 1000)
  `
  );
  run('UPDATE commands SET response = COALESCE(response, response_text)');

  // Seed default config values
  const now = new Date().toISOString();
  const defaults = [
    ['welcome_message', process.env.WELCOME_MESSAGE || 'Hi! I am the Datacube AU DM assistant. Send START to enable smart replies.'],
    ['rules_text', process.env.RULES_TEXT || 'Be respectful, stay on topic, and avoid spam.'],
    ['link_url', process.env.LINK_URL || 'https://datacube.au'],
    ['updates_text', process.env.UPDATES_TEXT || 'No updates at the moment. Use !updates again later.'],
    ['ai_enabled', process.env.AI_ENABLED || 'true'],
    ['ai_mode', process.env.AI_MODE || 'auto_detect'],
    ['ai_rate_limit_user', process.env.AI_RATE_LIMIT_USER || process.env.RATE_LIMIT_AI_PER_HOUR || '5'],
    ['ai_rate_limit_global', process.env.AI_RATE_LIMIT_GLOBAL || '30'],
    ['cache_ttl_days', process.env.CACHE_TTL_DAYS || '14'],
    ['reply_style', process.env.REPLY_STYLE || 'concise'],
    ['allow_image_analysis', process.env.ALLOW_IMAGE_ANALYSIS || 'false'],
    ['outbound_queue_delay_ms', process.env.OUTBOUND_QUEUE_DELAY_MS || '2500'],
    ['outbound_queue_min_delay_ms', process.env.OUTBOUND_QUEUE_MIN_DELAY_MS || '2000'],
    ['outbound_queue_max_delay_ms', process.env.OUTBOUND_QUEUE_MAX_DELAY_MS || '4000'],
    ['outbound_queue_max_attempts', process.env.OUTBOUND_QUEUE_MAX_ATTEMPTS || '5'],
    ['outbound_queue_send_timeout_ms', process.env.OUTBOUND_QUEUE_SEND_TIMEOUT_MS || '15000'],
    ['openrouter_model', process.env.OPENROUTER_MODEL || process.env.OPENROUTER_DEFAULT_MODEL || 'anthropic/claude-3-haiku'],
    ['openrouter_fallback_model', process.env.OPENROUTER_FALLBACK_MODEL || 'openai/gpt-4o-mini'],
    ['openrouter_timeout_ms', process.env.OPENROUTER_TIMEOUT_MS || '30000'],
    ['openrouter_retry_once', process.env.OPENROUTER_RETRY_ONCE || 'true'],
    ['openrouter_circuit_failure_threshold', process.env.OPENROUTER_CIRCUIT_FAILURE_THRESHOLD || '5'],
    ['openrouter_circuit_cooldown_ms', process.env.OPENROUTER_CIRCUIT_COOLDOWN_MS || '90000'],
    ['openrouter_max_tokens', process.env.OPENROUTER_MAX_TOKENS || '600'],
    ['openrouter_budget_daily_usd', process.env.OPENROUTER_BUDGET_DAILY_USD || '2.00'],
    ['rate_limit_ai_per_hour', process.env.RATE_LIMIT_AI_PER_HOUR || '5'],
    ['rate_limit_msg_per_day', process.env.RATE_LIMIT_MSG_PER_DAY || '50'],
    ['rate_limit_global_ai_per_minute', process.env.RATE_LIMIT_GLOBAL_AI_PER_MINUTE || '20'],
    ['bot_name', 'Datacube AU Bot'],
    ['broadcast_enabled', process.env.BROADCAST_ENABLED || 'true'],
    ['updates_message', process.env.UPDATES_TEXT || 'No updates at the moment. Use !updates again later.']
  ];

  for (const [key, value] of defaults) {
    // Check if key exists
    const existing = get('SELECT key FROM config WHERE key = ?', [key]);
    if (!existing) {
      run('INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)', [key, value, now]);
    }
  }

  const defaultCommands = [
    ['help', 'Show command list and usage guidance.'],
    ['rules', get('SELECT value FROM config WHERE key = ?', ['rules_text'])?.value || 'Be respectful, stay on topic, and avoid spam.'],
    ['link', get('SELECT value FROM config WHERE key = ?', ['link_url'])?.value || 'https://datacube.au'],
    ['updates', get('SELECT value FROM config WHERE key = ?', ['updates_text'])?.value || 'No updates at the moment. Use !updates again later.']
  ];

  for (const [name, response] of defaultCommands) {
    const existing = get('SELECT id FROM commands WHERE name = ?', [name]);
    if (!existing) {
      run(
        `
        INSERT INTO commands (name, description, response, response_text, use_ai, tags, enabled, created_at, updated_at)
        VALUES (?, ?, ?, ?, 0, 'default', 1, ?, ?)
      `,
        [name, `Default ${name.toUpperCase()} command`, response, response, now, now]
      );
    }
  }

  saveDb();
  logger.info('Database schema initialized');
}

function closeDb() {
  if (db) {
    saveDb();
    db.close();
    db = null;
  }
}

module.exports = { getDb, initSchema, closeDb, run, exec, get, all, saveDb };

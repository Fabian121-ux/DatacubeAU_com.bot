'use strict';

/**
 * Runtime config loader — reads from SQLite config table.
 * Falls back to .env values if DB not ready.
 * Provides a simple get/set interface for runtime config.
 */

const db = require('../db/database');

// In-memory cache with TTL
const cache = new Map();
const CACHE_TTL_MS = 30_000; // 30 seconds

function getCached(key) {
  const entry = cache.get(key);
  if (!entry) return null;
  if (Date.now() - entry.ts > CACHE_TTL_MS) {
    cache.delete(key);
    return null;
  }
  return entry.value;
}

function setCached(key, value) {
  cache.set(key, { value, ts: Date.now() });
}

/**
 * Get a config value by key.
 * Priority: DB → .env → defaultValue
 */
function getConfig(key, defaultValue = null) {
  const cached = getCached(key);
  if (cached !== null) return cached;

  try {
    const row = db.get('SELECT value FROM config WHERE key = ?', [key]);
    if (row) {
      setCached(key, row.value);
      return row.value;
    }
  } catch (_) {
    // DB not ready yet — fall through to env
  }

  // Fallback to environment variable
  const envVal = process.env[key.toUpperCase()] ?? defaultValue;
  return envVal;
}

/**
 * Set a config value in the DB.
 */
function setConfig(key, value) {
  const now = new Date().toISOString();
  
  // Check if key exists
  const existing = db.get('SELECT key FROM config WHERE key = ?', [key]);
  if (existing) {
    db.run('UPDATE config SET value = ?, updated_at = ? WHERE key = ?', [String(value), now, key]);
  } else {
    db.run('INSERT INTO config (key, value, updated_at) VALUES (?, ?, ?)', [key, String(value), now]);
  }
  setCached(key, String(value));
}

/**
 * Get all config entries as an object.
 */
function getAllConfig() {
  try {
    const rows = db.all('SELECT key, value, updated_at FROM config');
    return rows.reduce((acc, row) => {
      acc[row.key] = { value: row.value, updated_at: row.updated_at };
      return acc;
    }, {});
  } catch (_) {
    return {};
  }
}

/**
 * Convenience helpers for typed config values
 */
function getBool(key, defaultValue = false) {
  const val = getConfig(key, String(defaultValue));
  return val === 'true' || val === '1';
}

function getInt(key, defaultValue = 0) {
  const val = getConfig(key, String(defaultValue));
  return parseInt(val, 10) || defaultValue;
}

module.exports = { getConfig, setConfig, getAllConfig, getBool, getInt };

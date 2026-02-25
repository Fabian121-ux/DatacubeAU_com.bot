'use strict';

const db = require('./database');
const { normalizeQuestion, tokenOverlapScore, makeFingerprint } = require('../utils/text-normalizer');
const { getInt } = require('../utils/config-loader');

function getCacheTtlDays() {
  return getInt('cache_ttl_days', 14);
}

function findExactCache(question) {
  const normalized = normalizeQuestion(question);
  if (!normalized) return null;

  const nowIso = new Date().toISOString();
  const row = db.get(
    `
    SELECT * FROM qa_cache
    WHERE normalized_question = ?
      AND (expires_at IS NULL OR expires_at > ?)
  `,
    [normalized, nowIso]
  );

  if (!row) return null;

  db.run(
    `
    UPDATE qa_cache
    SET hit_count = hit_count + 1, last_used_at = ?
    WHERE id = ?
  `,
    [nowIso, row.id]
  );

  return row;
}

function findFuzzyCache(question, threshold = 0.62) {
  const normalized = normalizeQuestion(question);
  if (!normalized) return null;

  const nowIso = new Date().toISOString();
  const rows = db.all(
    `
    SELECT * FROM qa_cache
    WHERE expires_at IS NULL OR expires_at > ?
    ORDER BY last_used_at DESC
    LIMIT 150
  `,
    [nowIso]
  );

  let best = null;
  let bestScore = 0;

  for (const row of rows) {
    const score = tokenOverlapScore(normalized, row.normalized_question);
    if (score > bestScore) {
      best = row;
      bestScore = score;
    }
  }

  if (!best || bestScore < threshold) {
    return null;
  }

  db.run(
    `
    UPDATE qa_cache
    SET hit_count = hit_count + 1, last_used_at = ?
    WHERE id = ?
  `,
    [nowIso, best.id]
  );

  return { ...best, similarity: bestScore };
}

function saveCacheAnswer({ question, answerText, source = 'ai', model = null, ttlDays = null }) {
  const normalized = normalizeQuestion(question);
  if (!normalized || !answerText) return null;

  const now = new Date();
  const effectiveTtl = Number.isFinite(ttlDays) ? ttlDays : getCacheTtlDays();
  const expiresAt = new Date(now.getTime() + Math.max(1, effectiveTtl) * 24 * 3600 * 1000).toISOString();
  const nowIso = now.toISOString();
  const fingerprint = makeFingerprint(normalized);

  const existing = db.get('SELECT id FROM qa_cache WHERE normalized_question = ?', [normalized]);
  if (existing) {
    db.run(
      `
      UPDATE qa_cache
      SET answer_text = ?, source = ?, model = ?, embedding_hash_or_fingerprint = ?, created_at = ?, last_used_at = ?, expires_at = ?
      WHERE id = ?
    `,
      [answerText, source, model, fingerprint, nowIso, nowIso, expiresAt, existing.id]
    );
    return existing.id;
  }

  db.run(
    `
    INSERT INTO qa_cache (
      normalized_question,
      embedding_hash_or_fingerprint,
      answer_text,
      source,
      model,
      created_at,
      last_used_at,
      hit_count,
      expires_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
  `,
    [normalized, fingerprint, answerText, source, model, nowIso, nowIso, expiresAt]
  );

  const inserted = db.get('SELECT id FROM qa_cache WHERE normalized_question = ?', [normalized]);
  return inserted?.id || null;
}

function deleteExpiredCache() {
  const nowIso = new Date().toISOString();
  db.run('DELETE FROM qa_cache WHERE expires_at IS NOT NULL AND expires_at <= ?', [nowIso]);
}

function getCacheStats() {
  return (
    db.get(
      `
    SELECT
      COUNT(*) as total_entries,
      COALESCE(SUM(hit_count), 0) as total_hits,
      COALESCE(AVG(hit_count), 0) as avg_hits
    FROM qa_cache
  `
    ) || { total_entries: 0, total_hits: 0, avg_hits: 0 }
  );
}

module.exports = {
  findExactCache,
  findFuzzyCache,
  saveCacheAnswer,
  deleteExpiredCache,
  getCacheStats
};

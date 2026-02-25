'use strict';

const db = require('./database');

function logAiCall({ jid, model, promptTokens = 0, completionTokens = 0, costUsd = 0, success = 1 }) {
  const now = new Date().toISOString();

  db.run(
    `
    INSERT INTO ai_calls (jid, model, prompt_tokens, completion_tokens, cost_usd, success, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `,
    [jid, model, promptTokens, completionTokens, costUsd, success ? 1 : 0, now]
  );
}

function getRecentAiCalls({ limit = 50, offset = 0, jid = null } = {}) {
  if (jid) {
    return db.all(
      `
      SELECT * FROM ai_calls WHERE jid = ?
      ORDER BY timestamp DESC LIMIT ? OFFSET ?
    `,
      [jid, limit, offset]
    );
  }

  return db.all(
    `
    SELECT * FROM ai_calls
    ORDER BY timestamp DESC LIMIT ? OFFSET ?
  `,
    [limit, offset]
  );
}

function getAiCallStats() {
  return (
    db.get(
      `
    SELECT
      COUNT(*) as total_calls,
      COALESCE(SUM(prompt_tokens), 0) as total_prompt_tokens,
      COALESCE(SUM(completion_tokens), 0) as total_completion_tokens,
      COALESCE(SUM(cost_usd), 0) as total_cost_usd,
      COALESCE(SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END), 0) as successful_calls,
      COALESCE(SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END), 0) as failed_calls
    FROM ai_calls
  `
    ) || {
      total_calls: 0,
      total_prompt_tokens: 0,
      total_completion_tokens: 0,
      total_cost_usd: 0,
      successful_calls: 0,
      failed_calls: 0
    }
  );
}

function getTodayAiCallStats() {
  const dayStart = new Date();
  dayStart.setHours(0, 0, 0, 0);

  return (
    db.get(
      `
    SELECT
      COUNT(*) as total_calls,
      COALESCE(SUM(cost_usd), 0) as total_cost_usd
    FROM ai_calls
    WHERE timestamp >= ?
  `,
      [dayStart.toISOString()]
    ) || { total_calls: 0, total_cost_usd: 0 }
  );
}

function getAiCallsSince(isoTimestamp) {
  const row = db.get('SELECT COUNT(*) as count FROM ai_calls WHERE timestamp >= ?', [isoTimestamp]);
  return row ? row.count : 0;
}

module.exports = { logAiCall, getRecentAiCalls, getAiCallStats, getTodayAiCallStats, getAiCallsSince };

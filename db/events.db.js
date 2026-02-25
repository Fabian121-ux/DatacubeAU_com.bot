'use strict';

const db = require('./database');
const { hashJid } = require('../utils/text-normalizer');

function toSafeNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

function logEvent({
  messageId = null,
  jid = null,
  eventType = 'pipeline',
  stage = 'unknown',
  intent = null,
  routeCategory = null,
  topic = null,
  detail = null,
  success = true,
  cacheHit = false,
  aiCostUsd = 0
}) {
  const now = new Date();
  const nowIso = now.toISOString();
  const day = nowIso.slice(0, 10);
  const jidHash = jid ? hashJid(jid) : null;
  const safeCost = toSafeNumber(aiCostUsd, 0);

  db.run(
    `
    INSERT INTO events (
      message_id,
      jid_hash,
      event_type,
      stage,
      intent,
      route_category,
      topic,
      detail,
      success,
      cache_hit,
      ai_cost_usd,
      created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
    [
      messageId,
      jidHash,
      eventType,
      stage,
      intent,
      routeCategory,
      topic,
      detail,
      success ? 1 : 0,
      cacheHit ? 1 : 0,
      safeCost,
      nowIso
    ]
  );

  const incrementAi = routeCategory === 'AI_REQUIRED' ? 1 : 0;
  db.run(
    `
    INSERT INTO trends_daily (day, total_messages, ai_calls, cache_hits, ai_cost_usd, updated_at)
    VALUES (?, 1, ?, ?, ?, ?)
    ON CONFLICT(day) DO UPDATE SET
      total_messages = trends_daily.total_messages + 1,
      ai_calls = trends_daily.ai_calls + excluded.ai_calls,
      cache_hits = trends_daily.cache_hits + excluded.cache_hits,
      ai_cost_usd = trends_daily.ai_cost_usd + excluded.ai_cost_usd,
      updated_at = excluded.updated_at
  `,
    [day, incrementAi, cacheHit ? 1 : 0, safeCost, nowIso]
  );
}

function getRecentEvents({ limit = 100, offset = 0 } = {}) {
  return db.all(
    `
    SELECT id, message_id, event_type, stage, intent, route_category, topic, detail, success, cache_hit, ai_cost_usd, created_at
    FROM events
    ORDER BY created_at DESC
    LIMIT ? OFFSET ?
  `,
    [limit, offset]
  );
}

function getEventTotalsSince(sinceIso) {
  return (
    db.get(
      `
    SELECT
      COUNT(*) as total_messages,
      COALESCE(SUM(CASE WHEN route_category = 'AI_REQUIRED' THEN 1 ELSE 0 END), 0) as ai_calls,
      COALESCE(SUM(cache_hit), 0) as cache_hits,
      COALESCE(SUM(ai_cost_usd), 0) as ai_cost_usd
    FROM events
    WHERE created_at >= ?
  `,
      [sinceIso]
    ) || { total_messages: 0, ai_calls: 0, cache_hits: 0, ai_cost_usd: 0 }
  );
}

function getTopIntentsSince(sinceIso, limit = 10) {
  return db.all(
    `
    SELECT COALESCE(intent, route_category, 'unknown') as topic, COUNT(*) as count
    FROM events
    WHERE created_at >= ?
    GROUP BY COALESCE(intent, route_category, 'unknown')
    ORDER BY count DESC
    LIMIT ?
  `,
    [sinceIso, limit]
  );
}

function getTopCommandsSince(sinceIso, limit = 10) {
  return db.all(
    `
    SELECT COALESCE(intent, topic, 'command') as topic, COUNT(*) as count
    FROM events
    WHERE created_at >= ?
      AND route_category IN ('STATIC_COMMAND', 'CUSTOM_COMMAND')
    GROUP BY COALESCE(intent, topic, 'command')
    ORDER BY count DESC
    LIMIT ?
  `,
    [sinceIso, limit]
  );
}

function getDailyTrendSince(sinceIso, limit = 30) {
  return db.all(
    `
    SELECT
      day,
      total_messages,
      ai_calls,
      cache_hits,
      ai_cost_usd
    FROM trends_daily
    WHERE day >= substr(?, 1, 10)
    ORDER BY day DESC
    LIMIT ?
  `,
    [sinceIso, limit]
  );
}

module.exports = {
  logEvent,
  getRecentEvents,
  getEventTotalsSince,
  getTopIntentsSince,
  getTopCommandsSince,
  getDailyTrendSince
};


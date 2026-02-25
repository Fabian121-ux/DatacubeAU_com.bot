'use strict';

const {
  logEvent,
  getRecentEvents,
  getEventTotalsSince,
  getTopIntentsSince,
  getTopCommandsSince,
  getDailyTrendSince
} = require('./events.db');

function getSince(days = 7) {
  const safeDays = Math.max(1, Math.min(Number(days) || 7, 30));
  return new Date(Date.now() - safeDays * 24 * 3600 * 1000).toISOString();
}

function logTrendEvent({
  messageId = null,
  jid,
  category,
  topic = 'general',
  intent = null,
  stage = 'router',
  detail = null,
  wasAiUsed = false,
  cacheHit = false,
  aiCostUsd = 0
}) {
  logEvent({
    messageId,
    jid,
    eventType: 'router',
    stage,
    intent: intent || topic,
    routeCategory: category,
    topic,
    detail,
    cacheHit,
    aiCostUsd: wasAiUsed ? aiCostUsd : 0
  });
}

function getTrendsSummary({ days = 7 } = {}) {
  const since = getSince(days);
  const totals = getEventTotalsSince(since);
  const topTopics = getTopIntentsSince(since, 10);
  const topCommands = getTopCommandsSince(since, 10);
  const daily = getDailyTrendSince(since, 30);
  const cacheHitRate =
    Number(totals.total_messages) > 0
      ? Number(totals.cache_hits) / Number(totals.total_messages)
      : 0;

  return {
    totals,
    topTopics,
    topCommands,
    daily,
    cacheHitRate
  };
}

function getRecentTrendEvents(limit = 100, offset = 0) {
  return getRecentEvents({ limit, offset }).map((item) => ({
    id: item.id,
    category: item.route_category || item.event_type,
    topic: item.topic || item.intent || 'general',
    was_ai_used: item.route_category === 'AI_REQUIRED' ? 1 : 0,
    cache_hit: item.cache_hit || 0,
    ai_cost_usd: item.ai_cost_usd || 0,
    timestamp: item.created_at
  }));
}

module.exports = {
  logTrendEvent,
  getTrendsSummary,
  getRecentTrendEvents
};


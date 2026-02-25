'use strict';

const {
  getAiCallsThisHour,
  getGlobalAiCallsThisHour,
  getMessagesToday,
  incrementAiCalls,
  incrementGlobalAiCalls,
  incrementMessageCount
} = require('../db/rate-limits.db');
const { getInt } = require('./config-loader');
const logger = require('./logger');

function getUserAiLimit() {
  return getInt('ai_rate_limit_user', getInt('rate_limit_ai_per_hour', 5));
}

function getGlobalAiLimit() {
  return getInt('ai_rate_limit_global', 30);
}

function checkAiRateLimit(jid) {
  const maxPerHour = getUserAiLimit();
  const current = getAiCallsThisHour(jid);

  if (current >= maxPerHour) {
    logger.warn(`Rate limit hit (AI/hour) for ${jid}: ${current}/${maxPerHour}`);
    return {
      allowed: false,
      reason: `You have reached ${maxPerHour} AI replies this hour. Please wait and try again.`
    };
  }

  const globalMax = getGlobalAiLimit();
  const globalCurrent = getGlobalAiCallsThisHour();
  if (globalCurrent >= globalMax) {
    logger.warn(`Global AI rate limit hit: ${globalCurrent}/${globalMax}/hour`);
    return {
      allowed: false,
      reason: 'The assistant is at capacity right now. Please try again shortly or use HELP.'
    };
  }

  return { allowed: true, reason: null };
}

function checkMessageRateLimit(jid) {
  const maxPerDay = getInt('rate_limit_msg_per_day', 50);
  const current = getMessagesToday(jid);

  if (current >= maxPerDay) {
    logger.warn(`Rate limit hit (msg/day) for ${jid}: ${current}/${maxPerDay}`);
    return {
      allowed: false,
      reason: `You've sent too many messages today. Please try again tomorrow.`
    };
  }

  return { allowed: true, reason: null };
}

function recordAiCall(jid) {
  incrementAiCalls(jid);
  incrementGlobalAiCalls();
}

function recordMessage(jid) {
  incrementMessageCount(jid);
}

function getGlobalAiUsage() {
  return {
    count: getGlobalAiCallsThisHour(),
    limit: getGlobalAiLimit(),
    windowStart: null
  };
}

module.exports = {
  checkAiRateLimit,
  checkMessageRateLimit,
  recordAiCall,
  recordMessage,
  getGlobalAiUsage
};

'use strict';

const logger = require('../utils/logger');
const { upsertUser, isNewUser, getUser } = require('../db/users.db');
const { isDuplicateMessage, markMessageProcessed } = require('../db/processed-messages.db');
const { checkMessageRateLimit, checkAiRateLimit, recordMessage } = require('../utils/rate-limiter');
const { logInbound, logOutbound } = require('../utils/message-logger');
const { classifyIntent } = require('./intent-classifier');
const { findCustomCommandForText } = require('../db/commands.db');
const { findKnowledgeMatch } = require('../db/kb.db');
const { findExactCache, findFuzzyCache, saveCacheAnswer } = require('../db/qa-cache.db');
const { logTrendEvent } = require('../db/trends.db');
const { getBool, getConfig } = require('../utils/config-loader');
const { hasSensitiveContent } = require('../utils/text-normalizer');
const { sendQueued } = require('../utils/outbound-queue');

const { helpHandler } = require('../handlers/help.handler');
const { rulesHandler } = require('../handlers/rules.handler');
const { linkHandler } = require('../handlers/link.handler');
const { updatesHandler } = require('../handlers/updates.handler');
const { onboardHandler, handleOptIn, handleOptOut } = require('../handlers/onboard.handler');

const DEFAULT_COMMANDS = new Set(['help', 'rules', 'link', 'updates']);

let aiHandler = null;
function getAiHandler() {
  if (!aiHandler) {
    try {
      aiHandler = require('../ai/ai-handler');
    } catch (_) {
      aiHandler = null;
    }
  }
  return aiHandler;
}

function commandHandlerByIntent(intent) {
  switch (intent) {
    case 'help':
      return helpHandler;
    case 'rules':
      return rulesHandler;
    case 'link':
      return linkHandler;
    case 'updates':
      return updatesHandler;
    case 'optin':
      return handleOptIn;
    case 'optout':
      return handleOptOut;
    default:
      return null;
  }
}

function detectTopic(text = '', fallback = 'general') {
  const lower = text.toLowerCase();
  const rules = [
    ['login issues', /(login|signin|session|auth)/],
    ['upload errors', /(upload|image|file|media)/],
    ['deployment', /(deploy|vps|nginx|pm2|docker)/],
    ['database', /(db|database|sqlite|postgres|query)/],
    ['rate limits', /(rate limit|quota|too many)/],
    ['bot config', /(config|setting|admin|token)/],
    ['api issues', /(api|endpoint|request|response|http)/]
  ];

  for (const [topic, pattern] of rules) {
    if (pattern.test(lower)) return topic;
  }

  return fallback;
}

function isHumanHandoffNeeded(text = '') {
  const lower = text.toLowerCase();
  const patterns = [
    /(payment|invoice|billing|chargeback)/,
    /(account recovery|hacked|stolen account)/,
    /(bank|credit card|cvv|otp|password|token|private key|seed phrase)/,
    /(legal|lawsuit|court|lawyer)/
  ];
  return patterns.some((pattern) => pattern.test(lower));
}

function stripAiPrefix(text) {
  return text.replace(/^(dev:|guide:)\s*/i, '').trim();
}

function isExplicitAiPrompt(text) {
  return /^(dev:|guide:)\s*/i.test(text.trim());
}

async function sendReply(sock, jid, text, handler, source = handler, meta = {}) {
  await sendQueued(sock, jid, { text }, { source, numberId: meta.numberId });
  logOutbound(jid, text, handler, { numberId: meta.numberId, usedAi: meta.usedAi });
}

function logAudit({
  messageId = null,
  jid,
  category,
  topic = 'general',
  intent = null,
  stage = 'router',
  detail = null,
  cacheHit = false,
  aiCostUsd = 0
}) {
  logTrendEvent({
    messageId,
    jid,
    category,
    topic,
    intent,
    stage,
    detail,
    wasAiUsed: category === 'AI_REQUIRED',
    cacheHit,
    aiCostUsd
  });
}

function markProcessed(messageId, jid, routeCategory, numberId) {
  markMessageProcessed(messageId, jid, routeCategory, numberId);
}

async function routeMessage(sock, { jid, text, name, messageId, numberId = null }) {
  const trimmedText = String(text || '').trim();
  const topic = detectTopic(trimmedText);

  if (messageId && isDuplicateMessage(messageId, numberId)) {
    logger.info(`Duplicate inbound message ignored: ${messageId}`);
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'duplicate',
      stage: 'dedupe',
      detail: 'duplicate_message'
    });
    return;
  }

  const wasNewUser = isNewUser(jid);
  upsertUser(jid, name);
  recordMessage(jid);
  logInbound(jid, trimmedText, 'pending', { numberId });

  const msgRateCheck = checkMessageRateLimit(jid);
  if (!msgRateCheck.allowed) {
    await sendReply(sock, jid, msgRateCheck.reason, 'ratelimit:daily', 'ratelimit:daily', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'rate_limit_daily',
      stage: 'rate_limit',
      detail: msgRateCheck.reason
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  if (wasNewUser) {
    await onboardHandler(sock, { jid, name, numberId });
    logOutbound(jid, '[onboard message]', 'onboard', { numberId, usedAi: false });
    logAudit({
      messageId,
      jid,
      category: 'STATIC_COMMAND',
      topic: 'onboarding',
      intent: 'onboard',
      stage: 'onboard'
    });
    markProcessed(messageId, jid, 'STATIC_COMMAND', numberId);
    return;
  }

  const staticIntent = classifyIntent(trimmedText);

  // Keep START/STOP deterministic and explicit regardless of custom command definitions.
  if (staticIntent === 'optin' || staticIntent === 'optout') {
    const handler = commandHandlerByIntent(staticIntent);
    if (handler) {
      await handler(sock, { jid, text: trimmedText, name, numberId });
      logOutbound(jid, `[rule:${staticIntent}]`, `rule:${staticIntent}`, { numberId, usedAi: false });
      logAudit({
        messageId,
        jid,
        category: 'STATIC_COMMAND',
        topic: staticIntent,
        intent: staticIntent,
        stage: 'static_command'
      });
      markProcessed(messageId, jid, 'STATIC_COMMAND', numberId);
      return;
    }
  }

  const customCommandMatch = findCustomCommandForText(trimmedText);
  if (customCommandMatch) {
    const { command, args } = customCommandMatch;

    if (!command.use_ai) {
      await sendReply(sock, jid, command.response_text, `custom:${command.name}`, 'custom_command', { numberId });
      const category = DEFAULT_COMMANDS.has(command.name) ? 'STATIC_COMMAND' : 'CUSTOM_COMMAND';
      logAudit({
        messageId,
        jid,
        category,
        topic: command.name,
        intent: command.name,
        stage: 'custom_command',
        detail: 'deterministic_response'
      });
      markProcessed(messageId, jid, category, numberId);
      return;
    }

    const ai = getAiHandler();
    if (!ai) {
      const fallback = 'AI service is not available right now. Please try again later.';
      await sendReply(sock, jid, fallback, 'ai:unavailable', 'ai:unavailable', { numberId });
      logAudit({
        messageId,
        jid,
        category: 'HUMAN_HANDOFF',
        topic: 'ai_unavailable',
        intent: command.name,
        stage: 'custom_command'
      });
      markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
      return;
    }

    const aiInput = `${command.response_text}\n\nUser request:\n${args || trimmedText}`;
    const aiResult = await ai.handleAiMessage(sock, { jid, text: aiInput, name, numberId });
    logAudit({
      messageId,
      jid,
      category: 'AI_REQUIRED',
      topic: `custom:${command.name}`,
      intent: command.name,
      stage: 'ai_custom_command',
      aiCostUsd: aiResult?.costUsd || 0
    });
    markProcessed(messageId, jid, 'AI_REQUIRED', numberId);
    return;
  }

  // Keep fallback static handlers for loose aliases like "hi".
  if (staticIntent) {
    const handler = commandHandlerByIntent(staticIntent);
    if (handler) {
      await handler(sock, { jid, text: trimmedText, name, numberId });
      logOutbound(jid, `[rule:${staticIntent}]`, `rule:${staticIntent}`, { numberId, usedAi: false });
      logAudit({
        messageId,
        jid,
        category: 'STATIC_COMMAND',
        topic: staticIntent,
        intent: staticIntent,
        stage: 'static_command'
      });
      markProcessed(messageId, jid, 'STATIC_COMMAND', numberId);
      return;
    }
  }

  if (isHumanHandoffNeeded(trimmedText) || hasSensitiveContent(trimmedText)) {
    const handoff =
      'This request looks account/payment/security related. For safety, please contact a human admin directly.';
    await sendReply(sock, jid, handoff, 'handoff', 'handoff', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic,
      stage: 'safety_gate'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  const kbMatch = findKnowledgeMatch(trimmedText);
  if (kbMatch?.bestMatch) {
    const snippet = kbMatch.bestMatch.chunk_text.slice(0, 1400);
    const kbAnswer = `Knowledge Base (${kbMatch.bestMatch.title}):\n${snippet}`;
    await sendReply(sock, jid, kbAnswer, 'kb_match', 'kb', { numberId });
    saveCacheAnswer({
      question: trimmedText,
      answerText: kbAnswer,
      source: 'kb',
      model: 'kb-retrieval'
    });
    logAudit({
      messageId,
      jid,
      category: 'CACHE_HIT',
      topic: kbMatch.bestMatch.source_type || topic,
      intent: 'kb_match',
      stage: 'knowledge_base',
      cacheHit: true
    });
    markProcessed(messageId, jid, 'CACHE_HIT', numberId);
    return;
  }

  const exactCache = findExactCache(trimmedText);
  if (exactCache) {
    await sendReply(sock, jid, exactCache.answer_text, 'cache:exact', 'cache', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'CACHE_HIT',
      topic,
      intent: 'cache_exact',
      stage: 'cache',
      cacheHit: true
    });
    markProcessed(messageId, jid, 'CACHE_HIT', numberId);
    return;
  }

  const fuzzyCache = findFuzzyCache(trimmedText);
  if (fuzzyCache) {
    await sendReply(sock, jid, fuzzyCache.answer_text, 'cache:fuzzy', 'cache', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'CACHE_HIT',
      topic,
      intent: 'cache_fuzzy',
      stage: 'cache',
      cacheHit: true
    });
    markProcessed(messageId, jid, 'CACHE_HIT', numberId);
    return;
  }

  const user = getUser(jid);
  if (!user || !user.opted_in) {
    const optInMsg = 'To get AI-powered guidance, send START to opt in. Use !help for commands.';
    await sendReply(sock, jid, optInMsg, 'gate:optin_required', 'gate:optin_required', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'optin_required',
      stage: 'ai_gate'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  if (!getBool('ai_enabled', true)) {
    const aiDisabledMsg = 'AI is currently disabled by admin. You can still use HELP, RULES, LINK, and UPDATES.';
    await sendReply(sock, jid, aiDisabledMsg, 'gate:ai_disabled', 'gate:ai_disabled', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'ai_disabled',
      stage: 'ai_gate'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  const aiMode = getConfig('ai_mode', 'auto_detect');
  const explicitRequired = aiMode === 'explicit_only';
  if (explicitRequired && !isExplicitAiPrompt(trimmedText)) {
    const explicitMsg = "AI is in explicit mode. Start your message with 'DEV:' or 'GUIDE:' to request AI help.";
    await sendReply(sock, jid, explicitMsg, 'gate:explicit_only', 'gate:explicit_only', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'explicit_only',
      stage: 'ai_gate'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  const rateCheck = checkAiRateLimit(jid);
  if (!rateCheck.allowed) {
    await sendReply(sock, jid, rateCheck.reason, 'gate:ai_ratelimited', 'gate:ai_ratelimited', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'ai_rate_limited',
      stage: 'ai_gate'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  const ai = getAiHandler();
  if (!ai) {
    const fallback = 'AI service is not available right now. Please try again later.';
    await sendReply(sock, jid, fallback, 'ai:unavailable', 'ai:unavailable', { numberId });
    logAudit({
      messageId,
      jid,
      category: 'HUMAN_HANDOFF',
      topic: 'ai_unavailable',
      stage: 'ai'
    });
    markProcessed(messageId, jid, 'HUMAN_HANDOFF', numberId);
    return;
  }

  const aiInput = explicitRequired ? stripAiPrefix(trimmedText) : trimmedText;
  const aiResult = await ai.handleAiMessage(sock, { jid, text: aiInput, name, numberId });
  logAudit({
    messageId,
    jid,
    category: 'AI_REQUIRED',
    topic,
    intent: 'ai_required',
    stage: 'ai',
    aiCostUsd: aiResult?.costUsd || 0
  });
  markProcessed(messageId, jid, 'AI_REQUIRED', numberId);
}

module.exports = { routeMessage };

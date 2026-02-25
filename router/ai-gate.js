'use strict';

/**
 * AI Gate — determines if a message qualifies for AI processing.
 * Phase 1: stub that returns false (AI not yet integrated).
 * Phase 2: full topic classification + opt-in check.
 *
 * Decision tree:
 * 1. Is user opted-in? → No → send opt-in prompt
 * 2. Is AI globally enabled? → No → send "AI offline"
 * 3. Has user exceeded AI rate limit? → Yes → send rate limit message
 * 4. Is topic programming/tech? → No → send "I only answer tech questions"
 * 5. → Route to AI handler
 */

const { getUser } = require('../db/users.db');
const { checkAiRateLimit } = require('../utils/rate-limiter');
const { getBool } = require('../utils/config-loader');
const logger = require('../utils/logger');

// Tech topic keywords for classification
const TECH_KEYWORDS = [
  'code', 'error', 'bug', 'function', 'api', 'database', 'deploy', 'docker',
  'node', 'python', 'react', 'next', 'nextjs', 'supabase', 'qdrant', 'rag',
  'vector', 'auth', 'jwt', 'sql', 'query', 'architecture', 'datacube',
  'backend', 'frontend', 'vps', 'server', 'npm', 'git', 'github', 'typescript',
  'javascript', 'js', 'ts', 'css', 'html', 'rest', 'graphql', 'webhook',
  'async', 'await', 'promise', 'callback', 'class', 'object', 'array',
  'string', 'integer', 'boolean', 'null', 'undefined', 'import', 'export',
  'module', 'package', 'install', 'build', 'test', 'debug', 'log', 'console',
  'http', 'https', 'url', 'endpoint', 'request', 'response', 'json', 'xml',
  'redis', 'mongodb', 'postgres', 'mysql', 'sqlite', 'orm', 'prisma',
  'express', 'fastify', 'koa', 'hapi', 'nestjs', 'django', 'flask', 'rails',
  'kubernetes', 'k8s', 'nginx', 'apache', 'ssl', 'tls', 'certificate',
  'env', 'environment', 'config', 'variable', 'secret', 'key', 'token',
  'how', 'why', 'what', 'when', 'where', 'which', 'help', 'explain',
  'implement', 'create', 'build', 'fix', 'solve', 'issue', 'problem'
];

/**
 * Check if message text contains tech-related keywords.
 * @param {string} text
 * @returns {boolean}
 */
function isTechTopic(text) {
  if (!text) return false;
  const lower = text.toLowerCase();
  return TECH_KEYWORDS.some(kw => lower.includes(kw));
}

/**
 * Evaluate whether a message should be routed to AI.
 * @param {string} jid
 * @param {string} text
 * @returns {{ route: 'ai'|'optin_prompt'|'ai_offline'|'rate_limited'|'off_topic', reason: string|null }}
 */
function evaluateAiGate(jid, text) {
  // 1. Check opt-in status
  const user = getUser(jid);
  if (!user || !user.opted_in) {
    return {
      route: 'optin_prompt',
      reason: `🤖 To get AI-powered replies, send *START* to opt in.\n\nType \`!help\` for all commands.`
    };
  }

  // 2. Check if AI is globally enabled
  const aiEnabled = getBool('ai_enabled', true);
  if (!aiEnabled) {
    return {
      route: 'ai_offline',
      reason: `🔧 AI replies are temporarily offline. Please try again later.\n\nType \`!help\` for other commands.`
    };
  }

  // 3. Check per-user AI rate limit
  const rateCheck = checkAiRateLimit(jid);
  if (!rateCheck.allowed) {
    return {
      route: 'rate_limited',
      reason: rateCheck.reason
    };
  }

  // 4. Topic classification
  if (!isTechTopic(text)) {
    return {
      route: 'off_topic',
      reason: `🤖 I only answer programming and tech questions.\n\nTry asking about code, architecture, or Datacube AU.\nType \`!help\` for commands.`
    };
  }

  return { route: 'ai', reason: null };
}

module.exports = { evaluateAiGate, isTechTopic };

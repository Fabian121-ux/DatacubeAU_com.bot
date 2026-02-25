'use strict';

const { logMessage } = require('../db/messages.db');
const logger = require('./logger');

/**
 * Unified message logger — logs both inbound and outbound messages.
 * Stores only 100-char preview for privacy.
 */

/**
 * Log an inbound message from a user.
 * @param {string} jid
 * @param {string} content
 * @param {string} handler - which handler processed it
 * @param {{ numberId?: number|null, usedAi?: boolean }} [meta]
 */
function logInbound(jid, content, handler = 'unknown', meta = {}) {
  try {
    logMessage({
      jid,
      direction: 'in',
      content,
      handler,
      usedAi: Boolean(meta.usedAi),
      numberId: meta.numberId ?? null
    });
  } catch (err) {
    logger.error('Failed to log inbound message', { jid, err: err.message });
  }
}

/**
 * Log an outbound message sent by the bot.
 * @param {string} jid
 * @param {string} content
 * @param {string} handler - which handler generated it
 * @param {{ numberId?: number|null, usedAi?: boolean }} [meta]
 */
function logOutbound(jid, content, handler = 'unknown', meta = {}) {
  try {
    logMessage({
      jid,
      direction: 'out',
      content,
      handler,
      usedAi: Boolean(meta.usedAi),
      numberId: meta.numberId ?? null
    });
  } catch (err) {
    logger.error('Failed to log outbound message', { jid, err: err.message });
  }
}

module.exports = { logInbound, logOutbound };

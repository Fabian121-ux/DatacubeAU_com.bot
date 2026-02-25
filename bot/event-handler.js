'use strict';

/**
 * Event handler — listens to messages.upsert from Baileys.
 * Filters noise (self, status, groups) and routes to message-router.
 * DM-only MVP: group messages are silently ignored.
 */

const logger = require('../utils/logger');
const { routeMessage } = require('../router/message-router');

/**
 * Extract text content from a Baileys message object.
 * Handles text, extended text, and button reply messages.
 */
function extractText(msg) {
  const m = msg.message;
  if (!m) return '';

  return (
    m.conversation ||
    m.extendedTextMessage?.text ||
    m.buttonsResponseMessage?.selectedDisplayText ||
    m.listResponseMessage?.title ||
    m.templateButtonReplyMessage?.selectedDisplayText ||
    ''
  );
}

/**
 * Extract sender JID from a message.
 * For DMs: remoteJid is the user's JID.
 */
function extractJid(msg) {
  return msg.key?.remoteJid || null;
}

/**
 * Extract sender display name.
 */
function extractName(msg) {
  return msg.pushName || null;
}

function extractMessageId(msg) {
  return msg.key?.id || null;
}

/**
 * Main message handler — registered with wa-client.js.
 * @param {object} sock - Baileys socket
 * @param {object} msg - Baileys message object
 */
async function handleMessage(sock, msg, context = {}) {
  try {
    const jid = extractJid(msg);
    if (!jid) return;
    const numberId = context.numberId ?? null;

    // ── FILTER: Ignore self-sent messages ──
    if (msg.key?.fromMe) return;

    // ── FILTER: Ignore status broadcasts ──
    if (jid === 'status@broadcast') return;

    // ── FILTER: Ignore group messages (DM-only MVP) ──
    if (jid.endsWith('@g.us')) {
      logger.debug(`Ignoring group message from ${jid}`);
      return;
    }

    // ── FILTER: Ignore non-DM JIDs ──
    if (!jid.endsWith('@s.whatsapp.net')) {
      logger.debug(`Ignoring non-DM JID: ${jid}`);
      return;
    }

    const text = extractText(msg);
    const name = extractName(msg);
    const messageId = extractMessageId(msg);

    logger.info(`📨 DM from ${jid} (${name || 'unknown'}): "${text.slice(0, 60)}"`);

    // Route to message router
    await routeMessage(sock, { jid, text, name, messageId, msg, numberId });

  } catch (err) {
    logger.error('Unhandled error in event-handler', { err: err.message, stack: err.stack });
  }
}

module.exports = { handleMessage };

'use strict';

const logger = require('../utils/logger');
const { sendQueued } = require('../utils/outbound-queue');

const HELP_TEXT = `👋 *Welcome to Datacube AU Bot!*

I'm your AI assistant for programming, architecture, and Datacube AU questions.

*Commands:*
• \`!help\` or \`help\` — Show this message
• \`!rules\` — Community rules
• \`!link\` — Useful links & resources
• \`!updates\` — Latest Datacube AU news
• \`START\` — Opt in to AI replies

*AI Assistant:*
Just ask me any programming or tech question and I'll do my best to help! 🤖

_Powered by Datacube AU_`;

/**
 * Handle !help, help, hi commands.
 * @param {object} sock - Baileys socket
 * @param {object} ctx - { jid, text, name }
 */
async function helpHandler(sock, { jid, name, numberId = null }) {
  logger.info(`help.handler triggered for ${jid}`);

  await sendQueued(sock, jid, { text: HELP_TEXT }, { numberId });
  return 'rule:help';
}

module.exports = { helpHandler };

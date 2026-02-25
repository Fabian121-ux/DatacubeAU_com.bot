'use strict';

const logger = require('../utils/logger');
const { getConfig } = require('../utils/config-loader');
const { sendQueued } = require('../utils/outbound-queue');

/**
 * Handle !updates, news commands.
 * Returns latest Datacube AU announcements.
 * Content can be updated via admin panel config.
 */
async function updatesHandler(sock, { jid, numberId = null }) {
  logger.info(`updates.handler triggered for ${jid}`);

  // Allow admin to update this via config table
  const customUpdates = getConfig('updates_text', getConfig('updates_message', null));

  const updatesText = customUpdates || `📢 *Datacube AU — Latest Updates*

🚀 *Bot Launch (Feb 2026)*
The Datacube AU WhatsApp AI Assistant is now live! Ask me any programming or architecture question.

🤖 *AI Features*
• Context-aware answers about Datacube AU's stack
• Programming help (Node.js, React, Next.js, Supabase, Qdrant)
• Architecture guidance

📅 *Coming Soon*
• RAG-powered document search
• Image understanding (error screenshots)
• Multi-language support

_Type \`START\` to enable AI replies._
_Type \`!help\` for all commands._`;

  await sendQueued(sock, jid, { text: updatesText }, { numberId });
  return 'rule:updates';
}

module.exports = { updatesHandler };

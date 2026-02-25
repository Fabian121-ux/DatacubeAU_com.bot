'use strict';

const logger = require('../utils/logger');
const { getConfig } = require('../utils/config-loader');
const { sendQueued } = require('../utils/outbound-queue');

const LINKS_TEXT = `🔗 *Datacube AU Resources*

*Website & Platform:*
• 🌐 Website: https://datacube.au
• 📚 Documentation: https://docs.datacube.au
• 🐙 GitHub: https://github.com/datacube-au

*Community:*
• 💬 Discord: https://discord.gg/datacube-au
• 🐦 Twitter/X: https://twitter.com/datacube_au
• 📧 Contact: hello@datacube.au

*Developer Resources:*
• 🛠️ API Docs: https://api.datacube.au/docs
• 📦 NPM Packages: https://npmjs.com/org/datacube-au
• 🗺️ Roadmap: https://datacube.au/roadmap

_Type \`!help\` for available commands._`;

/**
 * Handle !link, links commands.
 */
async function linkHandler(sock, { jid, numberId = null }) {
  logger.info(`link.handler triggered for ${jid}`);
  const linkUrl = getConfig('link_url', 'https://datacube.au');
  const text = `${LINKS_TEXT}\n\nPrimary Link: ${linkUrl}`;
  await sendQueued(sock, jid, { text }, { numberId });
  return 'rule:link';
}

module.exports = { linkHandler };

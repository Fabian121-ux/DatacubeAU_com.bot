'use strict';

const logger = require('../utils/logger');
const { getConfig } = require('../utils/config-loader');
const { sendQueued } = require('../utils/outbound-queue');

const RULES_TEXT = `📋 *Datacube AU Community Rules*

1. *Be respectful* — Treat everyone with courtesy and professionalism.

2. *Stay on topic* — This bot is for programming, tech, and Datacube AU questions.

3. *No spam* — Don't flood the bot with repeated messages.

4. *No harmful content* — No offensive, illegal, or harmful requests.

5. *Privacy* — Don't share personal information of others.

6. *AI limitations* — The AI may make mistakes. Always verify critical information.

7. *Opt-in required* — Send \`START\` to enable AI replies.

_By using this bot, you agree to these rules._
_Questions? Contact the Datacube AU admin team._`;

/**
 * Handle !rules, rules commands.
 */
async function rulesHandler(sock, { jid, numberId = null }) {
  logger.info(`rules.handler triggered for ${jid}`);
  const customRules = getConfig('rules_text', RULES_TEXT) || RULES_TEXT;
  await sendQueued(sock, jid, { text: customRules }, { numberId });
  return 'rule:rules';
}

module.exports = { rulesHandler };

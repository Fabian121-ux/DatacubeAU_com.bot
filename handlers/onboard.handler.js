'use strict';

const logger = require('../utils/logger');
const { setOptIn } = require('../db/users.db');
const { getConfig } = require('../utils/config-loader');
const { sendQueued } = require('../utils/outbound-queue');

const WELCOME_TEXT = `Welcome to Datacube AU Bot.

I am your AI assistant for programming, architecture, and Datacube AU questions.

To get started, reply with START to enable AI-powered replies.

Quick commands:
- !help
- !rules
- !link
- !updates`;

const OPT_IN_CONFIRMED = `You are all set.

AI replies are now enabled. Ask any programming or tech question.

Type !help to see all commands.`;

async function onboardHandler(sock, { jid, name, numberId = null }) {
  logger.info(`onboard.handler triggered for new user ${jid} (${name || 'unknown'})`);

  const customWelcome = getConfig('welcome_message', WELCOME_TEXT) || WELCOME_TEXT;
  const greeting = name ? `Hi ${name}!` : 'Hello!';
  const text = `${greeting}\n\n${customWelcome}`;

  await sendQueued(sock, jid, { text }, { numberId });
  return 'onboard';
}

async function handleOptIn(sock, { jid, numberId = null }) {
  logger.info(`User opted in: ${jid}`);
  setOptIn(jid, true);
  await sendQueued(sock, jid, { text: OPT_IN_CONFIRMED }, { numberId });
  return 'optin';
}

async function handleOptOut(sock, { jid, numberId = null }) {
  logger.info(`User opted out: ${jid}`);
  setOptIn(jid, false);
  await sendQueued(
    sock,
    jid,
    { text: "You have been opted out. Send START anytime to re-enable AI replies." },
    { numberId }
  );
  return 'optout';
}

module.exports = { onboardHandler, handleOptIn, handleOptOut };

'use strict';

/**
 * Intent classifier — keyword + regex matching for commands.
 * Returns the matched intent or null.
 */

const INTENTS = [
  {
    name: 'help',
    patterns: [/^!help$/i, /^help$/i, /^hi$/i, /^hello$/i, /^hey$/i, /^hiya$/i]
  },
  {
    name: 'rules',
    patterns: [/^!rules$/i, /^rules$/i]
  },
  {
    name: 'link',
    patterns: [/^!link$/i, /^!links$/i, /^links?$/i, /^resources?$/i]
  },
  {
    name: 'updates',
    patterns: [/^!updates?$/i, /^news$/i, /^announcements?$/i, /^whats new$/i, /^what's new$/i]
  },
  {
    name: 'optin',
    patterns: [/^start$/i, /^opt.?in$/i, /^enable ai$/i, /^yes$/i]
  },
  {
    name: 'optout',
    patterns: [/^stop$/i, /^opt.?out$/i, /^disable ai$/i, /^unsubscribe$/i]
  }
];

/**
 * Classify a message text into an intent.
 * @param {string} text
 * @returns {string|null} intent name or null
 */
function classifyIntent(text) {
  if (!text || typeof text !== 'string') return null;

  const trimmed = text.trim();

  for (const intent of INTENTS) {
    for (const pattern of intent.patterns) {
      if (pattern.test(trimmed)) {
        return intent.name;
      }
    }
  }

  return null;
}

module.exports = { classifyIntent };

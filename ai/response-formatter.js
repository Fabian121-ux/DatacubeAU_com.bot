'use strict';

/**
 * Response Formatter — cleans and truncates AI responses for WhatsApp.
 * WhatsApp supports: *bold*, _italic_, ~strikethrough~, ```code```
 * Removes: markdown headers (##), HTML tags, excessive whitespace
 */

const MAX_LENGTH = 4000; // WhatsApp message limit (practical)
const SOFT_LIMIT = 1500; // Preferred max for readability

/**
 * Format AI response for WhatsApp delivery.
 * @param {string} text - Raw AI response
 * @returns {string} WhatsApp-safe formatted text
 */
function formatResponse(text) {
  if (!text) return '';

  let formatted = text
    // Remove markdown headers (## Header → *Header*)
    .replace(/^#{1,6}\s+(.+)$/gm, '*$1*')
    // Remove HTML tags
    .replace(/<[^>]+>/g, '')
    // Normalize multiple blank lines to max 2
    .replace(/\n{3,}/g, '\n\n')
    // Trim leading/trailing whitespace
    .trim();

  // Truncate if too long
  if (formatted.length > MAX_LENGTH) {
    formatted = formatted.slice(0, MAX_LENGTH - 50) + '\n\n_[Response truncated — ask for more details]_';
  }

  return formatted;
}

/**
 * Add a "thinking" indicator prefix for long responses.
 * @param {string} text
 * @returns {string}
 */
function addThinkingPrefix(text) {
  return `🤖 ${text}`;
}

module.exports = { formatResponse, addThinkingPrefix };

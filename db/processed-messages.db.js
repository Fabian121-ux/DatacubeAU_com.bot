'use strict';

const db = require('./database');

function dedupeKey(messageId, numberId = null) {
  if (!messageId) return null;
  if (numberId === null || numberId === undefined) {
    return String(messageId);
  }
  return `${Number(numberId)}:${String(messageId)}`;
}

function isDuplicateMessage(messageId, numberId = null) {
  if (!messageId) return false;
  const key = dedupeKey(messageId, numberId);
  const row = db.get('SELECT message_id FROM processed_messages WHERE message_id = ?', [key]);
  return Boolean(row);
}

function markMessageProcessed(messageId, jid, routeCategory = null, numberId = null) {
  if (!messageId) return;
  const key = dedupeKey(messageId, numberId);
  const now = new Date().toISOString();
  db.run(
    `
    INSERT OR REPLACE INTO processed_messages (message_id, jid, route_category, processed_at, number_id)
    VALUES (?, ?, ?, ?, ?)
  `,
    [key, jid, routeCategory, now, numberId === null || numberId === undefined ? null : Number(numberId)]
  );
}

module.exports = {
  isDuplicateMessage,
  markMessageProcessed
};

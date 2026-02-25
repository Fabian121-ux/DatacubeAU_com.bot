'use strict';

const db = require('./database');

/**
 * Log a message interaction (stores only first 100 chars).
 * @param {object} params
 * @param {string} params.jid
 * @param {'in'|'out'} params.direction
 * @param {string} params.content
 * @param {string} params.handler
 * @param {boolean|number} [params.usedAi]
 * @param {number|null} [params.numberId]
 */
function logMessage({
  jid,
  direction,
  content = '',
  handler = 'unknown',
  usedAi = false,
  numberId = null
}) {
  const preview = String(content).slice(0, 100);
  const now = new Date().toISOString();
  const ts = Date.now();
  const usedAiInt = usedAi ? 1 : 0;
  const normalizedNumberId =
    numberId === null || numberId === undefined ? null : Number(numberId);

  db.run(
    `
    INSERT INTO messages (
      jid,
      preview,
      ts,
      used_ai,
      number_id,
      direction,
      content_preview,
      handler,
      timestamp
    )
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
    [jid, preview, ts, usedAiInt, normalizedNumberId, direction, preview, handler, now]
  );
}

function getRecentMessages({ limit = 50, offset = 0, jid = null } = {}) {
  if (jid) {
    return db.all(
      `
      SELECT * FROM messages
      WHERE jid = ?
      ORDER BY COALESCE(ts, CAST(strftime('%s', timestamp) AS INTEGER) * 1000) DESC
      LIMIT ? OFFSET ?
    `,
      [jid, limit, offset]
    );
  }

  return db.all(
    `
    SELECT * FROM messages
    ORDER BY COALESCE(ts, CAST(strftime('%s', timestamp) AS INTEGER) * 1000) DESC
    LIMIT ? OFFSET ?
  `,
    [limit, offset]
  );
}

function getMessageCountToday(jid) {
  const dayStart = new Date();
  dayStart.setHours(0, 0, 0, 0);

  const row = db.get(
    `
    SELECT COUNT(*) as count FROM messages
    WHERE jid = ? AND direction = 'in' AND timestamp >= ?
  `,
    [jid, dayStart.toISOString()]
  );

  return row ? row.count : 0;
}

function getTotalMessageCount() {
  const result = db.get("SELECT COUNT(*) as count FROM messages WHERE direction = 'in'");
  return result ? result.count : 0;
}

module.exports = { logMessage, getRecentMessages, getMessageCountToday, getTotalMessageCount };

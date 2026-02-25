'use strict';

const db = require('./database');
const GLOBAL_KEY = '__global__';

function getRateLimit(jid) {
  const now = new Date().toISOString();
  const today = new Date();
  today.setHours(0, 0, 0, 0);

  let row = db.get('SELECT * FROM rate_limits WHERE jid = ?', [jid]);

  if (!row) {
    db.run(
      `
      INSERT INTO rate_limits (jid, ai_calls_this_hour, window_start, total_messages_today, day_start)
      VALUES (?, 0, ?, 0, ?)
    `,
      [jid, now, today.toISOString()]
    );
    row = db.get('SELECT * FROM rate_limits WHERE jid = ?', [jid]);
  }

  return row;
}

function incrementAiCalls(jid) {
  const now = new Date();
  const row = getRateLimit(jid);

  const windowStart = new Date(row.window_start);
  const windowExpired = now.getTime() - windowStart.getTime() > 3600_000; // 1 hour

  if (windowExpired) {
    db.run(
      `
      UPDATE rate_limits
      SET ai_calls_this_hour = 1, window_start = ?
      WHERE jid = ?
    `,
      [now.toISOString(), jid]
    );
    return;
  }

  db.run(
    `
    UPDATE rate_limits
    SET ai_calls_this_hour = ai_calls_this_hour + 1
    WHERE jid = ?
  `,
    [jid]
  );
}

function incrementMessageCount(jid) {
  const now = new Date();
  const row = getRateLimit(jid);

  const dayStart = new Date(row.day_start);
  const dayExpired = now.toDateString() !== dayStart.toDateString();

  if (dayExpired) {
    const newDayStart = new Date();
    newDayStart.setHours(0, 0, 0, 0);
    db.run(
      `
      UPDATE rate_limits
      SET total_messages_today = 1, day_start = ?
      WHERE jid = ?
    `,
      [newDayStart.toISOString(), jid]
    );
    return;
  }

  db.run(
    `
    UPDATE rate_limits
    SET total_messages_today = total_messages_today + 1
    WHERE jid = ?
  `,
    [jid]
  );
}

function getAiCallsThisHour(jid) {
  const row = db.get('SELECT * FROM rate_limits WHERE jid = ?', [jid]);
  if (!row) return 0;

  const windowStart = new Date(row.window_start);
  const windowExpired = Date.now() - windowStart.getTime() > 3600_000;
  return windowExpired ? 0 : row.ai_calls_this_hour;
}

function getMessagesToday(jid) {
  const row = db.get('SELECT * FROM rate_limits WHERE jid = ?', [jid]);
  if (!row) return 0;

  const dayStart = new Date(row.day_start);
  const dayExpired = new Date().toDateString() !== dayStart.toDateString();
  return dayExpired ? 0 : row.total_messages_today;
}

module.exports = {
  getRateLimit,
  incrementAiCalls,
  incrementGlobalAiCalls: () => incrementAiCalls(GLOBAL_KEY),
  incrementMessageCount,
  getAiCallsThisHour,
  getGlobalAiCallsThisHour: () => getAiCallsThisHour(GLOBAL_KEY),
  getMessagesToday
};

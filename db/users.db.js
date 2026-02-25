'use strict';

const db = require('./database');

/**
 * Upsert a user record. Creates on first contact, updates last_seen + count on subsequent.
 * @param {string} jid
 * @param {string|null} name
 * @returns {object}
 */
function upsertUser(jid, name = null) {
  const now = new Date().toISOString();

  const existing = db.get('SELECT * FROM users WHERE jid = ?', [jid]);

  if (!existing) {
    db.run(
      `
      INSERT INTO users (jid, name, opted_in, first_seen, last_seen, message_count, ai_call_count)
      VALUES (?, ?, 0, ?, ?, 1, 0)
    `,
      [jid, name, now, now]
    );
    return db.get('SELECT * FROM users WHERE jid = ?', [jid]);
  }

  db.run(
    `
    UPDATE users
    SET last_seen = ?, message_count = message_count + 1, name = COALESCE(?, name)
    WHERE jid = ?
  `,
    [now, name, jid]
  );

  return db.get('SELECT * FROM users WHERE jid = ?', [jid]);
}

function isNewUser(jid) {
  const row = db.get('SELECT id FROM users WHERE jid = ?', [jid]);
  return !row;
}

function getUser(jid) {
  return db.get('SELECT * FROM users WHERE jid = ?', [jid]);
}

function setOptIn(jid, optedIn) {
  db.run('UPDATE users SET opted_in = ? WHERE jid = ?', [optedIn ? 1 : 0, jid]);
}

function incrementAiCallCount(jid) {
  db.run('UPDATE users SET ai_call_count = ai_call_count + 1 WHERE jid = ?', [jid]);
}

function getAllUsers({ limit = 100, offset = 0 } = {}) {
  return db.all(
    `
    SELECT * FROM users
    ORDER BY last_seen DESC
    LIMIT ? OFFSET ?
  `,
    [limit, offset]
  );
}

function getOptedInUsers() {
  return db.all('SELECT * FROM users WHERE opted_in = 1 ORDER BY last_seen DESC');
}

function getUserCount() {
  const result = db.get('SELECT COUNT(*) as count FROM users');
  return result ? result.count : 0;
}

module.exports = {
  upsertUser,
  isNewUser,
  getUser,
  setOptIn,
  incrementAiCallCount,
  getAllUsers,
  getOptedInUsers,
  getUserCount
};

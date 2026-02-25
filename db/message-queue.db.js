'use strict';

const db = require('./database');

function nowIso() {
  return new Date().toISOString();
}

function enqueueMessage({ jid, payload, source = 'unknown', maxAttempts = 5, numberId = null }) {
  const now = nowIso();
  const normalizedNumberId =
    numberId === null || numberId === undefined ? null : Number(numberId);
  db.run(
    `
    INSERT INTO message_queue (
      jid,
      number_id,
      payload_json,
      source,
      status,
      attempt_count,
      max_attempts,
      next_attempt_at,
      created_at,
      updated_at
    ) VALUES (?, ?, ?, ?, 'queued', 0, ?, ?, ?, ?)
  `,
    [jid, normalizedNumberId, JSON.stringify(payload), source, maxAttempts, now, now, now]
  );

  const row = db.get('SELECT id FROM message_queue WHERE rowid = last_insert_rowid()');
  return row?.id || null;
}

function getMessageById(id) {
  return db.get('SELECT * FROM message_queue WHERE id = ?', [id]);
}

function claimNextMessage() {
  const now = nowIso();
  const row = db.get(
    `
    SELECT * FROM message_queue
    WHERE (status = 'queued' OR status = 'retry')
      AND dead_letter = 0
      AND next_attempt_at <= ?
    ORDER BY created_at ASC
    LIMIT 1
  `,
    [now]
  );

  if (!row) return null;

  db.run(
    `
    UPDATE message_queue
    SET status = 'sending',
        attempt_count = attempt_count + 1,
        updated_at = ?
    WHERE id = ?
  `,
    [now, row.id]
  );

  return getMessageById(row.id);
}

function markSent(id) {
  const now = nowIso();
  db.run(
    `
    UPDATE message_queue
    SET status = 'sent',
        sent_at = ?,
        updated_at = ?,
        last_error = NULL
    WHERE id = ?
  `,
    [now, now, id]
  );
}

function scheduleRetry(id, errorMessage, nextAttemptAt) {
  const now = nowIso();
  db.run(
    `
    UPDATE message_queue
    SET status = 'retry',
        next_attempt_at = ?,
        last_error = ?,
        updated_at = ?
    WHERE id = ?
  `,
    [nextAttemptAt, String(errorMessage || 'send failed').slice(0, 500), now, id]
  );
}

function markDeadLetter(id, errorMessage) {
  const now = nowIso();
  db.run(
    `
    UPDATE message_queue
    SET status = 'dead_letter',
        dead_letter = 1,
        last_error = ?,
        updated_at = ?
    WHERE id = ?
  `,
    [String(errorMessage || 'dead letter').slice(0, 500), now, id]
  );
}

function releaseInflightMessages() {
  const now = nowIso();
  db.run(
    `
    UPDATE message_queue
    SET status = 'queued',
        next_attempt_at = ?,
        updated_at = ?
    WHERE status = 'sending'
  `,
    [now, now]
  );
}

function getQueueStats() {
  return (
    db.get(
      `
    SELECT
      COALESCE(SUM(CASE WHEN status = 'queued' THEN 1 ELSE 0 END), 0) as queued,
      COALESCE(SUM(CASE WHEN status = 'retry' THEN 1 ELSE 0 END), 0) as retrying,
      COALESCE(SUM(CASE WHEN status = 'sending' THEN 1 ELSE 0 END), 0) as sending,
      COALESCE(SUM(CASE WHEN status = 'sent' THEN 1 ELSE 0 END), 0) as sent,
      COALESCE(SUM(CASE WHEN status = 'dead_letter' THEN 1 ELSE 0 END), 0) as dead_letter
    FROM message_queue
  `
    ) || { queued: 0, retrying: 0, sending: 0, sent: 0, dead_letter: 0 }
  );
}

module.exports = {
  enqueueMessage,
  getMessageById,
  claimNextMessage,
  markSent,
  scheduleRetry,
  markDeadLetter,
  releaseInflightMessages,
  getQueueStats
};

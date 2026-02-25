'use strict';

const db = require('./database');

const ALLOWED_STATUS = new Set(['idle', 'pairing', 'connected', 'disconnected']);

function normalizePhone(phone) {
  let digits = String(phone || '').replace(/\D/g, '');
  if (!digits) {
    throw new Error('phone is required');
  }
  if (digits.startsWith('00')) {
    digits = digits.slice(2);
  }
  if (digits.startsWith('0')) {
    const countryCode = String(process.env.WA_DEFAULT_COUNTRY_CODE || '').replace(/\D/g, '');
    if (!countryCode) {
      throw new Error('phone must include country code (set WA_DEFAULT_COUNTRY_CODE for local numbers)');
    }
    digits = `${countryCode}${digits.slice(1)}`;
  }
  if (digits.length < 8 || digits.length > 15) {
    throw new Error('phone must be 8-15 digits in E.164 format');
  }
  return digits;
}

function normalizeStatus(status) {
  const value = String(status || '').trim().toLowerCase();
  if (!ALLOWED_STATUS.has(value)) {
    throw new Error(`invalid status: ${status}`);
  }
  return value;
}

function mapRow(row) {
  if (!row) return null;
  return {
    ...row,
    id: Number(row.id),
    last_connected_at: row.last_connected_at ? Number(row.last_connected_at) : null,
    created_at: row.created_at ? Number(row.created_at) : null
  };
}

function listBotNumbers() {
  const rows = db.all(
    `
    SELECT id, phone, label, status, last_connected_at, created_at
    FROM bot_numbers
    ORDER BY created_at DESC, id DESC
  `
  );
  return rows.map(mapRow);
}

function getBotNumberById(id) {
  if (!Number.isFinite(Number(id))) return null;
  const row = db.get(
    `
    SELECT id, phone, label, status, last_connected_at, created_at
    FROM bot_numbers
    WHERE id = ?
  `,
    [Number(id)]
  );
  return mapRow(row);
}

function getBotNumberByPhone(phone) {
  const normalized = normalizePhone(phone);
  const row = db.get(
    `
    SELECT id, phone, label, status, last_connected_at, created_at
    FROM bot_numbers
    WHERE phone = ?
  `,
    [normalized]
  );
  return mapRow(row);
}

function createBotNumber({ phone, label = '' }) {
  const normalized = normalizePhone(phone);
  const now = Date.now();

  db.run(
    `
    INSERT INTO bot_numbers (phone, label, status, created_at)
    VALUES (?, ?, 'idle', ?)
  `,
    [normalized, String(label || '').trim(), now]
  );

  return getBotNumberByPhone(normalized);
}

function updateBotNumber(id, updates = {}) {
  const existing = getBotNumberById(id);
  if (!existing) return null;

  const phone =
    updates.phone !== undefined ? normalizePhone(updates.phone) : existing.phone;
  const label =
    updates.label !== undefined ? String(updates.label || '').trim() : existing.label;
  const status =
    updates.status !== undefined ? normalizeStatus(updates.status) : existing.status;
  const lastConnectedAt =
    updates.last_connected_at !== undefined
      ? updates.last_connected_at === null
        ? null
        : Number(updates.last_connected_at)
      : existing.last_connected_at;

  db.run(
    `
    UPDATE bot_numbers
    SET phone = ?, label = ?, status = ?, last_connected_at = ?
    WHERE id = ?
  `,
    [phone, label, status, lastConnectedAt, Number(id)]
  );

  return getBotNumberById(id);
}

function updateBotNumberStatus(id, status, options = {}) {
  const normalizedStatus = normalizeStatus(status);
  const now = Date.now();
  const lastConnectedAt =
    options.lastConnectedAt !== undefined
      ? options.lastConnectedAt
      : normalizedStatus === 'connected'
        ? now
        : null;

  db.run(
    `
    UPDATE bot_numbers
    SET status = ?, last_connected_at = ?
    WHERE id = ?
  `,
    [normalizedStatus, lastConnectedAt, Number(id)]
  );

  return getBotNumberById(id);
}

function deleteBotNumber(id) {
  const existing = getBotNumberById(id);
  if (!existing) return false;
  db.run('DELETE FROM bot_numbers WHERE id = ?', [Number(id)]);
  return true;
}

module.exports = {
  normalizePhone,
  listBotNumbers,
  getBotNumberById,
  getBotNumberByPhone,
  createBotNumber,
  updateBotNumber,
  updateBotNumberStatus,
  deleteBotNumber
};

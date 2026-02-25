'use strict';

const db = require('./database');

function normalizeCommandName(name = '') {
  return String(name).trim().toLowerCase().replace(/^!+/, '');
}

function hydrateCommand(row) {
  if (!row) return null;
  const responseText = row.response_text || row.response || '';
  return {
    ...row,
    response_text: responseText,
    response: row.response || responseText
  };
}

function parseTags(tags) {
  if (Array.isArray(tags)) {
    return tags.map((tag) => String(tag).trim()).filter(Boolean).join(',');
  }
  return String(tags || '')
    .split(',')
    .map((tag) => tag.trim())
    .filter(Boolean)
    .join(',');
}

function listCommands({ includeDisabled = true } = {}) {
  const sql = includeDisabled
    ? 'SELECT * FROM commands ORDER BY name ASC'
    : 'SELECT * FROM commands WHERE enabled = 1 ORDER BY name ASC';
  return db.all(sql).map(hydrateCommand);
}

function getCommandById(id) {
  return hydrateCommand(db.get('SELECT * FROM commands WHERE id = ?', [id]));
}

function getCommandByName(name) {
  const normalized = normalizeCommandName(name);
  if (!normalized) return null;
  return hydrateCommand(db.get('SELECT * FROM commands WHERE name = ?', [normalized]));
}

function createCommand({ name, description = '', responseText = '', useAi = false, tags = '', enabled = true }) {
  const normalized = normalizeCommandName(name);
  if (!normalized) {
    throw new Error('Command name is required');
  }
  if (!responseText || !String(responseText).trim()) {
    throw new Error('response_text is required');
  }

  const now = new Date().toISOString();
  db.run(
    `
    INSERT INTO commands (name, description, response, response_text, use_ai, tags, enabled, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `,
    [
      normalized,
      String(description || '').trim(),
      String(responseText).trim(),
      String(responseText).trim(),
      useAi ? 1 : 0,
      parseTags(tags),
      enabled ? 1 : 0,
      now,
      now
    ]
  );

  return getCommandByName(normalized);
}

function updateCommand(id, updates = {}) {
  const existing = getCommandById(id);
  if (!existing) {
    return null;
  }

  const next = {
    name: updates.name !== undefined ? normalizeCommandName(updates.name) : existing.name,
    description: updates.description !== undefined ? String(updates.description || '').trim() : existing.description,
    response_text: updates.responseText !== undefined ? String(updates.responseText || '').trim() : existing.response_text,
    use_ai: updates.useAi !== undefined ? (updates.useAi ? 1 : 0) : existing.use_ai,
    tags: updates.tags !== undefined ? parseTags(updates.tags) : existing.tags,
    enabled: updates.enabled !== undefined ? (updates.enabled ? 1 : 0) : existing.enabled
  };

  if (!next.name) {
    throw new Error('Command name is required');
  }
  if (!next.response_text) {
    throw new Error('response_text is required');
  }

  const now = new Date().toISOString();
  db.run(
    `
    UPDATE commands
    SET name = ?, description = ?, response = ?, response_text = ?, use_ai = ?, tags = ?, enabled = ?, updated_at = ?
    WHERE id = ?
  `,
    [next.name, next.description, next.response_text, next.response_text, next.use_ai, next.tags, next.enabled, now, id]
  );

  return getCommandById(id);
}

function deleteCommand(id) {
  const existing = getCommandById(id);
  if (!existing) return false;
  db.run('DELETE FROM commands WHERE id = ?', [id]);
  return true;
}

function parseCommandInvocation(text = '') {
  const trimmed = String(text).trim();
  if (!trimmed) return { commandName: '', args: '' };

  const normalized = trimmed.toLowerCase();
  const [firstToken, ...rest] = normalized.split(/\s+/);
  const commandName = normalizeCommandName(firstToken);
  const args = String(trimmed).split(/\s+/).slice(1).join(' ').trim();
  return { commandName, args };
}

function findCustomCommandForText(text = '') {
  const { commandName, args } = parseCommandInvocation(text);
  if (!commandName) return null;

  const command = hydrateCommand(db.get(
    `
    SELECT * FROM commands
    WHERE name = ? AND enabled = 1
  `,
    [commandName]
  ));

  if (!command) return null;
  return { command, args };
}

module.exports = {
  normalizeCommandName,
  listCommands,
  getCommandById,
  getCommandByName,
  createCommand,
  updateCommand,
  deleteCommand,
  findCustomCommandForText
};

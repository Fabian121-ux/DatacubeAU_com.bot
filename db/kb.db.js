'use strict';

const db = require('./database');
const {
  normalizeQuestion,
  tokenize,
  tokenOverlapScore,
  makeFingerprint
} = require('../utils/text-normalizer');

const MAX_DOCUMENT_BYTES = 512 * 1024;
const DEFAULT_CHUNK_SIZE = 900;
const DEFAULT_CHUNK_OVERLAP = 120;

function nowIso() {
  return new Date().toISOString();
}

function normalizeSourceType(sourceType = '') {
  const allowed = new Set(['conversation', 'site', 'architecture', 'general']);
  const normalized = String(sourceType || '').trim().toLowerCase();
  return allowed.has(normalized) ? normalized : 'general';
}

function chunkText(content = '', chunkSize = DEFAULT_CHUNK_SIZE, overlap = DEFAULT_CHUNK_OVERLAP) {
  const text = String(content).replace(/\r\n/g, '\n').trim();
  if (!text) return [];

  const chunks = [];
  let cursor = 0;
  while (cursor < text.length) {
    const end = Math.min(text.length, cursor + chunkSize);
    const slice = text.slice(cursor, end).trim();
    if (slice) chunks.push(slice);
    if (end >= text.length) break;
    cursor = Math.max(end - overlap, cursor + 1);
  }

  return chunks;
}

function extractKeywords(text = '', limit = 12) {
  const tokens = tokenize(text).filter((token) => token.length > 2);
  const unique = [];
  const seen = new Set();
  for (const token of tokens) {
    if (seen.has(token)) continue;
    seen.add(token);
    unique.push(token);
    if (unique.length >= limit) break;
  }
  return unique.join(' ');
}

function listDocuments({ limit = 50, offset = 0 } = {}) {
  return db.all(
    `
    SELECT id, title, source_type, fingerprint, tags, status, created_at, updated_at
    FROM kb_documents
    ORDER BY updated_at DESC
    LIMIT ? OFFSET ?
  `,
    [limit, offset]
  );
}

function getDocumentById(documentId) {
  return db.get('SELECT * FROM kb_documents WHERE id = ?', [documentId]);
}

function getDocumentChunks(documentId, { limit = 200, offset = 0 } = {}) {
  return db.all(
    `
    SELECT id, document_id, chunk_index, chunk_text, fingerprint, keywords, created_at
    FROM kb_chunks
    WHERE document_id = ?
    ORDER BY chunk_index ASC
    LIMIT ? OFFSET ?
  `,
    [documentId, limit, offset]
  );
}

function ingestDocument({ title, sourceType = 'general', content, tags = '' }) {
  const cleanTitle = String(title || '').trim();
  const cleanContent = String(content || '').trim();
  if (!cleanTitle) {
    throw new Error('title is required');
  }
  if (!cleanContent) {
    throw new Error('content is required');
  }
  const contentBytes = Buffer.byteLength(cleanContent, 'utf8');
  if (contentBytes > MAX_DOCUMENT_BYTES) {
    throw new Error(`content exceeds ${MAX_DOCUMENT_BYTES} bytes`);
  }

  const normalized = normalizeQuestion(cleanContent);
  const fingerprint = makeFingerprint(normalized);
  const chunks = chunkText(cleanContent);
  if (chunks.length === 0) {
    throw new Error('content did not produce valid chunks');
  }

  const now = nowIso();
  db.run(
    `
    INSERT INTO kb_documents (title, source_type, content, fingerprint, tags, status, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, 'active', ?, ?)
  `,
    [cleanTitle, normalizeSourceType(sourceType), cleanContent, fingerprint, String(tags || '').trim(), now, now]
  );

  const inserted = db.get(
    `
    SELECT id FROM kb_documents
    WHERE title = ? AND fingerprint = ? AND created_at = ?
    ORDER BY id DESC
    LIMIT 1
  `,
    [cleanTitle, fingerprint, now]
  );
  const documentId = inserted?.id;
  if (!documentId) {
    throw new Error('failed to persist kb document');
  }

  chunks.forEach((chunk, index) => {
    const chunkFingerprint = makeFingerprint(normalizeQuestion(chunk));
    db.run(
      `
      INSERT INTO kb_chunks (document_id, chunk_index, chunk_text, fingerprint, keywords, created_at)
      VALUES (?, ?, ?, ?, ?, ?)
    `,
      [documentId, index, chunk, chunkFingerprint, extractKeywords(chunk), now]
    );
  });

  return {
    document: getDocumentById(documentId),
    chunkCount: chunks.length
  };
}

function deleteDocument(documentId) {
  const doc = getDocumentById(documentId);
  if (!doc) return false;
  db.run('DELETE FROM kb_chunks WHERE document_id = ?', [documentId]);
  db.run('DELETE FROM kb_documents WHERE id = ?', [documentId]);
  return true;
}

function findKnowledgeMatch(question, { minScore = 0.34, limit = 3 } = {}) {
  const normalizedQuestion = normalizeQuestion(question);
  if (!normalizedQuestion) return null;

  const queryFingerprint = makeFingerprint(normalizedQuestion);
  const queryTokens = tokenize(normalizedQuestion).slice(0, 5);
  const likeConditions = [];
  const likeParams = [];

  for (const token of queryTokens) {
    likeConditions.push('c.keywords LIKE ?');
    likeParams.push(`%${token}%`);
  }

  const whereClause = likeConditions.length ? `AND (${likeConditions.join(' OR ')})` : '';
  const rows = db.all(
    `
    SELECT
      c.id,
      c.document_id,
      c.chunk_index,
      c.chunk_text,
      c.fingerprint,
      c.keywords,
      d.title,
      d.source_type
    FROM kb_chunks c
    JOIN kb_documents d ON d.id = c.document_id
    WHERE d.status = 'active'
      ${whereClause}
    ORDER BY d.updated_at DESC
    LIMIT 250
  `,
    likeParams
  );

  if (!rows.length) return null;

  let best = null;
  for (const row of rows) {
    const fingerprintBoost = row.fingerprint === queryFingerprint ? 0.25 : 0;
    const overlap = tokenOverlapScore(normalizedQuestion, row.chunk_text);
    const score = Math.min(1, overlap + fingerprintBoost);
    if (!best || score > best.score) {
      best = {
        ...row,
        score
      };
    }
  }

  if (!best || best.score < minScore) {
    return null;
  }

  const topMatches = rows
    .map((row) => ({
      ...row,
      score:
        tokenOverlapScore(normalizedQuestion, row.chunk_text) +
        (row.fingerprint === queryFingerprint ? 0.25 : 0)
    }))
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);

  return {
    bestMatch: best,
    matches: topMatches
  };
}

function getKnowledgeStats() {
  const docStats =
    db.get(
      `
    SELECT
      COUNT(*) as total_documents,
      COALESCE(SUM(CASE WHEN status = 'active' THEN 1 ELSE 0 END), 0) as active_documents
    FROM kb_documents
  `
    ) || { total_documents: 0, active_documents: 0 };

  const chunkStats =
    db.get(
      `
    SELECT COUNT(*) as total_chunks
    FROM kb_chunks
  `
    ) || { total_chunks: 0 };

  return { ...docStats, ...chunkStats };
}

module.exports = {
  MAX_DOCUMENT_BYTES,
  chunkText,
  listDocuments,
  getDocumentById,
  getDocumentChunks,
  ingestDocument,
  deleteDocument,
  findKnowledgeMatch,
  getKnowledgeStats
};

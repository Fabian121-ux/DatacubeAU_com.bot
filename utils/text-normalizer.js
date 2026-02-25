'use strict';

const crypto = require('crypto');

function normalizeQuestion(text = '') {
  return String(text)
    .toLowerCase()
    .trim()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .slice(0, 500);
}

function tokenize(text = '') {
  return normalizeQuestion(text)
    .split(' ')
    .filter((token) => token.length > 1);
}

function tokenOverlapScore(a, b) {
  const left = new Set(tokenize(a));
  const right = new Set(tokenize(b));
  if (left.size === 0 || right.size === 0) {
    return 0;
  }

  let intersection = 0;
  for (const token of left) {
    if (right.has(token)) intersection++;
  }

  const union = left.size + right.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

function makeFingerprint(normalizedQuestion) {
  return crypto.createHash('sha1').update(normalizedQuestion).digest('hex').slice(0, 16);
}

function hashJid(jid = '') {
  return crypto.createHash('sha1').update(String(jid)).digest('hex').slice(0, 10);
}

function hasSensitiveContent(text = '') {
  const lower = String(text).toLowerCase();
  const patterns = [
    /password/,
    /otp/,
    /bank/,
    /credit\s*card/,
    /cvv/,
    /account\s*number/,
    /secret/,
    /api[_\s-]?key/,
    /token/,
    /private\s*key/
  ];
  return patterns.some((pattern) => pattern.test(lower));
}

module.exports = {
  normalizeQuestion,
  tokenize,
  tokenOverlapScore,
  makeFingerprint,
  hashJid,
  hasSensitiveContent
};

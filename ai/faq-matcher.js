'use strict';

const fs = require('fs');
const path = require('path');
const { normalizeQuestion, tokenOverlapScore } = require('../utils/text-normalizer');

const FAQ_PATH = path.join(__dirname, '../context/faq.md');
let faqEntries = [];
let lastLoadedMs = 0;

function loadFaqEntries() {
  const now = Date.now();
  if (faqEntries.length > 0 && now - lastLoadedMs < 60_000) {
    return faqEntries;
  }

  let content = '';
  try {
    content = fs.readFileSync(FAQ_PATH, 'utf-8');
  } catch (_) {
    faqEntries = [];
    lastLoadedMs = now;
    return faqEntries;
  }

  const pairs = [];
  const regex = /\*\*Q:\s*(.+?)\*\*\s*\nA:\s*([\s\S]*?)(?=\n\*\*Q:|\n## |\n# |$)/g;
  let match;
  while ((match = regex.exec(content)) !== null) {
    const question = match[1].trim();
    const answer = match[2].trim();
    if (!question || !answer) continue;
    pairs.push({
      question,
      answer,
      normalized: normalizeQuestion(question)
    });
  }

  faqEntries = pairs;
  lastLoadedMs = now;
  return faqEntries;
}

function getFaqMatch(question) {
  const normalized = normalizeQuestion(question);
  if (!normalized) return null;

  const entries = loadFaqEntries();
  if (entries.length === 0) return null;

  const exact = entries.find((entry) => entry.normalized === normalized);
  if (exact) {
    return {
      kind: 'exact',
      answer: exact.answer,
      topic: exact.question.slice(0, 80)
    };
  }

  let best = null;
  let bestScore = 0;
  for (const entry of entries) {
    const score = tokenOverlapScore(normalized, entry.normalized);
    if (score > bestScore) {
      best = entry;
      bestScore = score;
    }
  }

  if (!best || bestScore < 0.55) {
    return null;
  }

  return {
    kind: 'fuzzy',
    answer: best.answer,
    topic: best.question.slice(0, 80),
    similarity: bestScore
  };
}

module.exports = { getFaqMatch };

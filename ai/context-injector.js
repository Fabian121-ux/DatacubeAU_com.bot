'use strict';

const fs = require('fs');
const path = require('path');
const logger = require('../utils/logger');

const CONTEXT_DIR = path.join(__dirname, '../context');
const contextCache = new Map();

function loadContextFile(filename) {
  if (contextCache.has(filename)) {
    return contextCache.get(filename);
  }

  const filePath = path.join(CONTEXT_DIR, filename);
  try {
    const content = fs.readFileSync(filePath, 'utf-8');
    contextCache.set(filename, content);
    return content;
  } catch (_) {
    logger.warn(`Context file not found: ${filename}`);
    contextCache.set(filename, '');
    return '';
  }
}

function getContext() {
  const files = ['architecture.md', 'datacube-architecture.md', 'stack-overview.md', 'faq.md', 'troubleshooting.md', 'links.md'];
  const sections = [];

  for (const file of files) {
    const content = loadContextFile(file);
    if (!content) continue;
    const sectionName = file.replace('.md', '').replace(/-/g, ' ').toUpperCase();
    sections.push(`=== ${sectionName} ===\n${content}`);
  }

  return sections.join('\n\n');
}

function invalidateCache() {
  contextCache.clear();
  logger.info('Context cache invalidated');
}

module.exports = { getContext, invalidateCache };

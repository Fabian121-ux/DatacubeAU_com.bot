'use strict';

/**
 * Seed context script — verifies context files exist and are readable.
 * Run after setup: node scripts/seed-context.js
 */

require('dotenv').config();
const fs = require('fs');
const path = require('path');

const CONTEXT_DIR = path.join(__dirname, '../context');
const CONTEXT_FILES = [
  'datacube-architecture.md',
  'stack-overview.md',
  'faq.md'
];

console.log('📚 Datacube AU Bot — Context Seed Check');
console.log('==========================================\n');

let allGood = true;

for (const file of CONTEXT_FILES) {
  const filePath = path.join(CONTEXT_DIR, file);
  if (fs.existsSync(filePath)) {
    const content = fs.readFileSync(filePath, 'utf-8');
    const lines = content.split('\n').length;
    const chars = content.length;
    console.log(`✅ ${file} — ${lines} lines, ${chars} chars`);
  } else {
    console.log(`❌ Missing: ${file}`);
    allGood = false;
  }
}

if (allGood) {
  console.log('\n✅ All context files present and readable.');
  console.log('   The AI will use these files to answer Datacube AU questions.\n');
} else {
  console.log('\n⚠️  Some context files are missing.');
  console.log('   Create them in the context/ directory.\n');
}

console.log('Context directory:', CONTEXT_DIR);

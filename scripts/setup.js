'use strict';

/**
 * Setup script: initializes database and required directories.
 * Run once before first start: node scripts/setup.js
 */

require('dotenv').config();
const fs = require('fs');
const path = require('path');

async function runSetup() {
  console.log('Datacube AU Bot - Setup');
  console.log('================================');

  const dirs = [
    process.env.LOG_DIR || './logs',
    path.dirname(process.env.DB_PATH || './data/datacube.db'),
    process.env.WA_SESSION_PATH || './session'
  ];

  for (const dir of dirs) {
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
      console.log(`Created directory: ${dir}`);
    } else {
      console.log(`Directory exists: ${dir}`);
    }
  }

  try {
    const { initSchema } = require('../db/database');
    await initSchema();
    console.log('Database schema initialized');
  } catch (err) {
    console.error(`Database initialization failed: ${err.message}`);
    process.exit(1);
  }

  if (!fs.existsSync('.env')) {
    console.log('\nNo .env file found.');
    console.log('Copy .env.example to .env and fill in your secrets.');
  } else {
    console.log('.env file found');

    const required = ['OPENROUTER_API_KEY', 'ADMIN_TOKEN'];
    const missing = required.filter((key) => !process.env[key] || process.env[key].includes('...'));

    if (missing.length > 0) {
      console.log(`\nMissing or placeholder env vars: ${missing.join(', ')}`);
      console.log('Edit .env and fill in real values before starting.');
    } else {
      console.log('Required env vars present');
    }
  }

  console.log('\n================================');
  console.log('Setup complete');
  console.log('Next steps:');
  console.log('1. Edit .env with your secrets');
  console.log('2. npm install');
  console.log('3. cd admin && npm install && npm run build && cd ..');
  console.log('4. node bot/index.js (or: pm2 start ecosystem.config.js)');
  console.log('5. Scan QR code with WhatsApp');
}

runSetup().catch((err) => {
  console.error(`Setup failed: ${err.message}`);
  process.exit(1);
});

'use strict';

/**
 * Health check script — verifies bot and API are running.
 * Can be used as a cron job or PM2 health check.
 * Exit code 0 = healthy, 1 = unhealthy.
 */

require('dotenv').config();
const http = require('http');

const API_PORT = process.env.API_PORT || 3001;
const ADMIN_TOKEN = process.env.ADMIN_TOKEN || process.env.API_SECRET_KEY || '';

function httpGet(url, headers = {}) {
  return new Promise((resolve, reject) => {
    const req = http.get(url, { headers }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try {
          resolve({ status: res.statusCode, body: JSON.parse(data) });
        } catch {
          resolve({ status: res.statusCode, body: data });
        }
      });
    });
    req.on('error', reject);
    req.setTimeout(5000, () => {
      req.destroy();
      reject(new Error('Request timeout'));
    });
  });
}

async function main() {
  console.log('🏥 Datacube AU Bot — Health Check');
  console.log('====================================\n');

  let healthy = true;

  // Check API health endpoint (no auth required)
  try {
    const res = await httpGet(`http://localhost:${API_PORT}/health`);
    if (res.status === 200) {
      console.log(`✅ API server: OK (port ${API_PORT})`);
    } else {
      console.log(`❌ API server: HTTP ${res.status}`);
      healthy = false;
    }
  } catch (err) {
    console.log(`❌ API server: ${err.message}`);
    healthy = false;
  }

  // Check bot status (requires auth)
  if (ADMIN_TOKEN) {
    try {
      const res = await httpGet(
        `http://localhost:${API_PORT}/api/v1/status`,
        { Authorization: `Bearer ${ADMIN_TOKEN}` }
      );
      if (res.status === 200) {
        const status = res.body;
        const icon = status.isConnected ? '✅' : status.isConnecting ? '⏳' : '❌';
        console.log(`${icon} Bot status: ${status.status} (uptime: ${status.uptime}s)`);
        if (!status.isConnected) healthy = false;
      } else {
        console.log(`❌ Bot status: HTTP ${res.status}`);
        healthy = false;
      }
    } catch (err) {
      console.log(`❌ Bot status: ${err.message}`);
      healthy = false;
    }
  } else {
    console.log('⚠️  ADMIN_TOKEN not set — skipping bot status check');
  }

  console.log('\n====================================');
  if (healthy) {
    console.log('✅ All systems healthy\n');
    process.exit(0);
  } else {
    console.log('❌ Health check FAILED\n');
    process.exit(1);
  }
}

main().catch(err => {
  console.error('Health check error:', err.message);
  process.exit(1);
});

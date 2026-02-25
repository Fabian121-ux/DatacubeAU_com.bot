'use strict';

require('dotenv').config();
const express = require('express');
const logger = require('../utils/logger');
const { initSchema, closeDb } = require('../db/database');
const { startClient, stopClient, setMessageHandler } = require('../bot/wa-client');
const { handleMessage } = require('../bot/event-handler');
const { startQueueWorker, stopQueueWorker } = require('../utils/outbound-queue');
const corsMiddleware = require('./middleware/cors.middleware');
const authMiddleware = require('./middleware/auth.middleware');

const statusRoute = require('./routes/status.route');
const qrRoute = require('./routes/qr.route');
const usersRoute = require('./routes/users.route');
const logsRoute = require('./routes/logs.route');
const broadcastRoute = require('./routes/broadcast.route');
const configRoute = require('./routes/config.route');
const botRoute = require('./routes/bot.route');
const adminRoute = require('./routes/admin.route');

const app = express();
const PORT = process.env.API_PORT || 3001;
const EMBED_WA_CLIENT = String(process.env.API_EMBED_WA_CLIENT || 'true') !== 'false';

app.use(corsMiddleware);
app.use(express.json({ limit: '1mb' }));
app.use(express.urlencoded({ extended: true }));

app.use((req, res, next) => {
  logger.info(`API ${req.method} ${req.path}`, { ip: req.ip });
  next();
});

app.get('/health', (req, res) => {
  res.json({ status: 'ok', timestamp: new Date().toISOString() });
});

// Legacy versioned routes
app.use('/api/v1', authMiddleware);
app.use('/api/v1/status', statusRoute);
app.use('/api/v1/qr', qrRoute);
app.use('/api/v1/users', usersRoute);
app.use('/api/v1/logs', logsRoute);
app.use('/api/v1/broadcast', broadcastRoute);
app.use('/api/v1/config', configRoute);

app.post('/api/v1/restart', authMiddleware, (req, res) => {
  logger.info('Restart requested via API');
  res.json({ message: 'Restart signal sent' });
  setTimeout(() => process.exit(0), 500);
});

// New admin and bot routes
app.use('/bot', authMiddleware, botRoute);
app.use('/admin', authMiddleware, adminRoute);

app.use((req, res) => {
  res.status(404).json({ error: `Route not found: ${req.method} ${req.path}` });
});

app.use((err, req, res, next) => {
  logger.error('Express error', { err: err.message, stack: err.stack });
  res.status(500).json({ error: 'Internal server error' });
});

async function startApiServer() {
  try {
    await initSchema();
  } catch (err) {
    logger.warn('DB init in API server (may already be initialized)', { err: err.message });
  }

  startQueueWorker();

  if (EMBED_WA_CLIENT) {
    setMessageHandler(handleMessage);
    startClient().catch((err) => {
      logger.error('Failed to start embedded WA client', { err: err.message, stack: err.stack });
    });
  } else {
    logger.warn('API_EMBED_WA_CLIENT is disabled; /bot/* endpoints may not reflect live state');
  }

  const server = app.listen(PORT, () => {
    logger.info(`API server running on port ${PORT}`);
  });

  const shutdown = async (signal) => {
    logger.info(`API received ${signal}, shutting down gracefully...`);
    stopQueueWorker();
    if (EMBED_WA_CLIENT) {
      await stopClient();
    }
    closeDb();
    server.close(() => {
      process.exit(0);
    });
    setTimeout(() => process.exit(0), 3000);
  };

  process.on('SIGINT', () => {
    shutdown('SIGINT').catch(() => process.exit(0));
  });
  process.on('SIGTERM', () => {
    shutdown('SIGTERM').catch(() => process.exit(0));
  });

  return server;
}

if (require.main === module) {
  startApiServer().catch((err) => {
    logger.error('Failed to start API server', { err: err.message, stack: err.stack });
    process.exit(1);
  });
}

module.exports = { app, startApiServer };

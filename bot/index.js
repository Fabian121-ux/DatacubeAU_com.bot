'use strict';

require('dotenv').config();
const logger = require('../utils/logger');
const { initSchema, closeDb } = require('../db/database');
const { startClient, stopClient, setMessageHandler } = require('./wa-client');
const { handleMessage } = require('./event-handler');
const { startQueueWorker, stopQueueWorker } = require('../utils/outbound-queue');

async function main() {
  logger.info('Starting Datacube AU Bot...');
  logger.info(`Environment: ${process.env.NODE_ENV || 'development'}`);

  try {
    await initSchema();
    logger.info('Database ready');
  } catch (err) {
    logger.error('Database initialization failed', { err: err.message });
    process.exit(1);
  }

  setMessageHandler(handleMessage);
  startQueueWorker();
  await startClient();
  logger.info('Bot startup complete and waiting for messages');
}

async function gracefulShutdown(signal) {
  logger.info(`Received ${signal}, shutting down gracefully...`);
  stopQueueWorker();
  await stopClient();
  closeDb();
  process.exit(0);
}

process.on('SIGINT', () => {
  gracefulShutdown('SIGINT').catch(() => process.exit(0));
});

process.on('SIGTERM', () => {
  gracefulShutdown('SIGTERM').catch(() => process.exit(0));
});

process.on('uncaughtException', (err) => {
  logger.error('Uncaught exception', { err: err.message, stack: err.stack });
  process.exit(1);
});

process.on('unhandledRejection', (reason) => {
  logger.error('Unhandled promise rejection', { reason: String(reason) });
});

main().catch((err) => {
  logger.error('Fatal startup error', { err: err.message, stack: err.stack });
  process.exit(1);
});


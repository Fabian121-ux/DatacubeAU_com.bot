'use strict';

const logger = require('./logger');
const { getInt } = require('./config-loader');
const {
  enqueueMessage,
  getMessageById,
  claimNextMessage,
  markSent,
  scheduleRetry,
  markDeadLetter,
  releaseInflightMessages
} = require('../db/message-queue.db');

let processing = false;
let workerTimer = null;

function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getQueueSettings() {
  const minDelay = Math.max(2000, getInt('outbound_queue_min_delay_ms', 2000));
  const maxDelay = Math.max(minDelay, getInt('outbound_queue_max_delay_ms', 4000));
  const sendTimeout = Math.max(5000, getInt('outbound_queue_send_timeout_ms', 15000));
  const maxAttempts = Math.max(1, getInt('outbound_queue_max_attempts', 5));
  return { minDelay, maxDelay, sendTimeout, maxAttempts };
}

function randomDispatchDelay() {
  const { minDelay, maxDelay } = getQueueSettings();
  if (maxDelay <= minDelay) return minDelay;
  return minDelay + Math.floor(Math.random() * (maxDelay - minDelay + 1));
}

function withTimeout(promise, ms) {
  let timer = null;
  const timeout = new Promise((_, reject) => {
    timer = setTimeout(() => reject(new Error(`send timeout after ${ms}ms`)), ms);
  });
  return Promise.race([promise, timeout]).finally(() => {
    if (timer) clearTimeout(timer);
  });
}

function computeBackoffMs(attemptCount) {
  const capped = Math.min(Math.max(1, attemptCount), 6);
  return Math.min(60_000, 1500 * 2 ** (capped - 1));
}

function getLiveSocket(preferredSock = null, numberId = null) {
  if (preferredSock) return preferredSock;
  try {
    const { getSock } = require('../bot/wa-client');
    return getSock(numberId);
  } catch {
    return null;
  }
}

async function processQueue(preferredSock = null) {
  if (processing) return;
  processing = true;

  try {
    while (true) {
      const item = claimNextMessage();
      if (!item) break;

      let payload = null;
      try {
        payload = JSON.parse(item.payload_json);
      } catch (err) {
        markDeadLetter(item.id, `invalid payload: ${err.message}`);
        continue;
      }

      const sock = getLiveSocket(preferredSock, item.number_id);
      if (!sock) {
        const retryAt = new Date(Date.now() + 5000).toISOString();
        scheduleRetry(item.id, 'whatsapp socket unavailable', retryAt);
        break;
      }

      const { sendTimeout } = getQueueSettings();
      try {
        await withTimeout(sock.sendMessage(item.jid, payload), sendTimeout);
        markSent(item.id);
      } catch (err) {
        const attempts = Number(item.attempt_count || 0);
        const maxAttempts = Number(item.max_attempts || getQueueSettings().maxAttempts);
        if (attempts >= maxAttempts) {
          markDeadLetter(item.id, err.message);
          logger.error('Outbound message moved to dead-letter', {
            queueId: item.id,
            jid: item.jid,
            attempts,
            err: err.message
          });
        } else {
          const retryAt = new Date(Date.now() + computeBackoffMs(attempts)).toISOString();
          scheduleRetry(item.id, err.message, retryAt);
        }
      }

      await sleep(randomDispatchDelay());
    }
  } finally {
    processing = false;
  }
}

function startQueueWorker() {
  if (workerTimer) return;
  releaseInflightMessages();
  workerTimer = setInterval(() => {
    processQueue().catch((err) => {
      logger.error('Queue worker error', { err: err.message });
    });
  }, 1000);
  logger.info('Outbound queue worker started');
}

function stopQueueWorker() {
  if (!workerTimer) return;
  clearInterval(workerTimer);
  workerTimer = null;
  logger.info('Outbound queue worker stopped');
}

async function waitForQueueResult(id, timeoutMs = 45_000) {
  const startedAt = Date.now();
  while (Date.now() - startedAt <= timeoutMs) {
    const row = getMessageById(id);
    if (!row) {
      throw new Error('queued message not found');
    }
    if (row.status === 'sent') {
      return row;
    }
    if (row.status === 'dead_letter') {
      throw new Error(row.last_error || 'message dead-lettered');
    }
    await sleep(250);
  }
  throw new Error(`queue delivery timeout after ${timeoutMs}ms`);
}

async function sendQueued(sock, jid, payload, options = {}) {
  const { awaitDelivery = true, source = 'bot', numberId = null } = options;
  const { maxAttempts } = getQueueSettings();
  const queueId = enqueueMessage({ jid, payload, source, maxAttempts, numberId });
  if (!queueId) {
    throw new Error('failed to enqueue outbound message');
  }

  processQueue(sock).catch((err) => {
    logger.error('Queue dispatch error', { err: err.message, queueId, jid });
  });

  if (!awaitDelivery) {
    return { id: queueId, status: 'queued' };
  }

  const result = await waitForQueueResult(queueId);
  return { id: queueId, status: result.status };
}

module.exports = {
  startQueueWorker,
  stopQueueWorker,
  processQueue,
  sendQueued
};

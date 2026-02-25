'use strict';

const { Router } = require('express');
const { getOptedInUsers } = require('../../db/users.db');
const { getSock, getBotState } = require('../../bot/wa-client');
const { logOutbound } = require('../../utils/message-logger');
const { sendQueued } = require('../../utils/outbound-queue');
const logger = require('../../utils/logger');

const router = Router();

let lastBroadcastTime = null;
const BROADCAST_COOLDOWN_MS = 24 * 60 * 60 * 1000;

router.post('/', async (req, res) => {
  const { message, dryRun = false, numberId = null } = req.body;

  if (!message || typeof message !== 'string' || message.trim().length === 0) {
    return res.status(400).json({ error: 'message is required' });
  }

  if (message.length > 4000) {
    return res.status(400).json({ error: 'message too long (max 4000 chars)' });
  }

  const botState = getBotState(numberId);
  if (!botState.isConnected && !dryRun) {
    return res.status(503).json({ error: 'Bot is not connected to WhatsApp' });
  }

  if (!dryRun && lastBroadcastTime) {
    const elapsed = Date.now() - lastBroadcastTime;
    if (elapsed < BROADCAST_COOLDOWN_MS) {
      const remaining = Math.ceil((BROADCAST_COOLDOWN_MS - elapsed) / 3600000);
      return res.status(429).json({
        error: `Broadcast rate limit: wait ${remaining} more hour(s) before next broadcast`
      });
    }
  }

  const users = getOptedInUsers();
  if (users.length === 0) {
    return res.json({ sent: 0, failed: 0, dryRun, message: 'No opted-in users' });
  }

  if (dryRun) {
    return res.json({
      dryRun: true,
      wouldSendTo: users.length,
      users: users.map((user) => ({ jid: user.jid, name: user.name }))
    });
  }

  const sock = getSock(numberId);
  if (!sock) {
    return res.status(503).json({ error: 'WhatsApp socket is not available' });
  }

  let sent = 0;
  let failed = 0;

  logger.info(`Broadcasting to ${users.length} opted-in users via queue`);

  for (const user of users) {
    try {
      await sendQueued(sock, user.jid, { text: message }, {
        awaitDelivery: false,
        source: 'broadcast',
        numberId: numberId === null || numberId === undefined ? botState.numberId : Number(numberId)
      });
      logOutbound(user.jid, message, 'broadcast', {
        numberId: numberId === null || numberId === undefined ? botState.numberId : Number(numberId),
        usedAi: false
      });
      sent++;
    } catch (err) {
      logger.error(`Broadcast failed for ${user.jid}`, { err: err.message });
      failed++;
    }
  }

  lastBroadcastTime = Date.now();
  logger.info(`Broadcast complete: ${sent} sent, ${failed} failed`);

  return res.json({ sent, failed, total: users.length, dryRun: false });
});

module.exports = router;

'use strict';

const { Router } = require('express');
const { getBotState } = require('../../bot/wa-client');
const { getUserCount } = require('../../db/users.db');
const { getTotalMessageCount } = require('../../db/messages.db');
const { getTodayAiCallStats } = require('../../db/ai-calls.db');

const router = Router();

router.get('/', (req, res) => {
  try {
    const botState = getBotState();
    const userCount = getUserCount();
    const messageCount = getTotalMessageCount();
    const todayAi = getTodayAiCallStats();

    const status = botState.isConnected
      ? 'online'
      : botState.isConnecting
        ? 'connecting'
        : 'offline';
    const lifecycleState = botState.state || botState.lifecycleState || botState.authState || 'booting';

    res.json({
      status,
      ready: botState.ready,
      state: lifecycleState,
      authState: lifecycleState,
      isConnected: botState.isConnected,
      isConnecting: botState.isConnecting,
      qrAvailable: botState.qrAvailable,
      hasQR: botState.hasQR,
      lastSeen: botState.lastSeen,
      lastConnectedAt: botState.lastConnectedAt || null,
      lastDisconnectReason: botState.lastDisconnectReason || null,
      lastError: botState.lastError || null,
      heartbeatAt: botState.heartbeatAt || null,
      uptime: botState.uptime,
      reconnectAttempts: botState.reconnectAttempts,
      stats: {
        totalUsers: userCount,
        totalMessages: messageCount,
        todayAiCalls: todayAi?.total_calls || 0,
        todayAiCost: todayAi?.total_cost_usd || 0
      },
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

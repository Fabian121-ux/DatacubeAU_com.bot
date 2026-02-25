'use strict';

const { Router } = require('express');
const { getRecentMessages } = require('../../db/messages.db');
const { getRecentAiCalls, getAiCallStats } = require('../../db/ai-calls.db');

const router = Router();

router.get('/', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '50', 10), 200);
    const offset = parseInt(req.query.offset || '0', 10);
    const jid = req.query.jid || null;
    const messages = getRecentMessages({ limit, offset, jid });
    res.json({ messages, count: messages.length, limit, offset });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.get('/ai', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '50', 10), 200);
    const offset = parseInt(req.query.offset || '0', 10);
    const jid = req.query.jid || null;
    const calls = getRecentAiCalls({ limit, offset, jid });
    const stats = getAiCallStats();
    res.json({ calls, stats, count: calls.length, limit, offset });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

module.exports = router;

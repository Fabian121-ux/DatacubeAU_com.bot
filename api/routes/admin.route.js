'use strict';

const { Router } = require('express');
const { getAllConfig, setConfig } = require('../../utils/config-loader');
const { invalidateCache } = require('../../ai/context-injector');
const { getRecentMessages } = require('../../db/messages.db');
const { getRecentAiCalls, getAiCallStats } = require('../../db/ai-calls.db');
const { getAllUsers, getUserCount, getOptedInUsers } = require('../../db/users.db');
const { getTrendsSummary, getRecentTrendEvents } = require('../../db/trends.db');
const { getCacheStats } = require('../../db/qa-cache.db');
const {
  listCommands,
  createCommand,
  updateCommand,
  deleteCommand
} = require('../../db/commands.db');
const {
  listDocuments,
  ingestDocument,
  deleteDocument,
  getDocumentChunks,
  getKnowledgeStats,
  MAX_DOCUMENT_BYTES
} = require('../../db/kb.db');
const { getQueueStats } = require('../../db/message-queue.db');
const {
  listBotNumbers,
  getBotNumberById,
  createBotNumber,
  updateBotNumber,
  deleteBotNumber
} = require('../../db/bot-numbers.db');
const { disconnectNumber } = require('../../bot/wa-client');
const logger = require('../../utils/logger');

const router = Router();

const ALLOWED_CONFIG_KEYS = [
  'welcome_message',
  'rules_text',
  'link_url',
  'updates_text',
  'updates_message',
  'ai_enabled',
  'ai_mode',
  'ai_rate_limit_user',
  'ai_rate_limit_global',
  'cache_ttl_days',
  'reply_style',
  'allow_image_analysis',
  'outbound_queue_delay_ms',
  'outbound_queue_min_delay_ms',
  'outbound_queue_max_delay_ms',
  'outbound_queue_max_attempts',
  'outbound_queue_send_timeout_ms',
  'openrouter_model',
  'openrouter_fallback_model',
  'openrouter_timeout_ms',
  'openrouter_retry_once',
  'openrouter_circuit_failure_threshold',
  'openrouter_circuit_cooldown_ms',
  'openrouter_max_tokens',
  'openrouter_budget_daily_usd',
  'rate_limit_ai_per_hour',
  'rate_limit_msg_per_day',
  'rate_limit_global_ai_per_minute',
  'bot_name',
  'broadcast_enabled'
];

router.get('/config', (req, res) => {
  try {
    const config = getAllConfig();
    const filtered = Object.fromEntries(
      Object.entries(config).filter(([key]) => ALLOWED_CONFIG_KEYS.includes(key))
    );
    return res.json({ config: filtered });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.put('/config', (req, res) => {
  try {
    const { key, value, updates } = req.body;
    const toUpdate = updates || (key ? { [key]: value } : null);
    if (!toUpdate || Object.keys(toUpdate).length === 0) {
      return res.status(400).json({ error: 'Provide key+value or updates object' });
    }

    const updated = [];
    const rejected = [];

    for (const [configKey, configValue] of Object.entries(toUpdate)) {
      if (!ALLOWED_CONFIG_KEYS.includes(configKey)) {
        rejected.push(configKey);
        continue;
      }
      setConfig(configKey, configValue);
      updated.push(configKey);
      logger.info(`Config updated: ${configKey} = ${configValue}`);
    }

    if (updated.some((configKey) => configKey.startsWith('context_'))) {
      invalidateCache();
    }

    return res.json({ updated, rejected, message: `${updated.length} config(s) updated` });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.post('/config/invalidate-context', (req, res) => {
  try {
    invalidateCache();
    return res.json({ message: 'Context cache invalidated - will reload on next AI call' });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/trends', (req, res) => {
  try {
    const days = Math.min(parseInt(req.query.days || '7', 10), 30);
    const trends = getTrendsSummary({ days });
    const cacheStats = getCacheStats();
    const aiStats = getAiCallStats();
    const queueStats = getQueueStats();
    const kbStats = getKnowledgeStats();
    return res.json({
      rangeDays: days,
      trends,
      cache: cacheStats,
      ai: aiStats,
      queue: queueStats,
      kb: kbStats
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/logs', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '50', 10), 200);
    const offset = parseInt(req.query.offset || '0', 10);
    const messages = getRecentMessages({ limit, offset });
    const aiCalls = getRecentAiCalls({ limit, offset });
    const events = getRecentTrendEvents(limit, offset);
    const queueStats = getQueueStats();
    return res.json({
      messages,
      aiCalls,
      events,
      queue: queueStats,
      count: {
        messages: messages.length,
        aiCalls: aiCalls.length,
        events: events.length
      }
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/users', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '100', 10), 500);
    const offset = parseInt(req.query.offset || '0', 10);
    const users = getAllUsers({ limit, offset });
    const total = getUserCount();
    const optedIn = getOptedInUsers().length;
    return res.json({
      users,
      pagination: { total, limit, offset, hasMore: offset + limit < total },
      summary: { optedIn }
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/numbers', (req, res) => {
  try {
    const numbers = listBotNumbers();
    return res.json({ numbers, count: numbers.length });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.post('/numbers', (req, res) => {
  try {
    const phone = req.body?.phone;
    const label = req.body?.label || '';
    if (!phone || !String(phone).trim()) {
      return res.status(400).json({ error: 'phone is required' });
    }
    const number = createBotNumber({ phone, label });
    return res.status(201).json({ number });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

router.put('/numbers/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid number id' });
    }

    const updates = {};
    if (req.body?.phone !== undefined) updates.phone = req.body.phone;
    if (req.body?.label !== undefined) updates.label = req.body.label;
    if (req.body?.status !== undefined) updates.status = req.body.status;
    if (req.body?.last_connected_at !== undefined) updates.last_connected_at = req.body.last_connected_at;

    const number = updateBotNumber(id, updates);
    if (!number) {
      return res.status(404).json({ error: 'Number not found' });
    }
    return res.json({ number });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

router.delete('/numbers/:id', async (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid number id' });
    }

    const existing = getBotNumberById(id);
    if (!existing) {
      return res.status(404).json({ error: 'Number not found' });
    }

    try {
      await disconnectNumber(id, { clearSession: true });
    } catch (_) {
      // Ignore disconnect errors on delete path.
    }

    deleteBotNumber(id);
    return res.json({ deleted: true, id });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/commands', (req, res) => {
  try {
    const includeDisabled = req.query.includeDisabled !== 'false';
    const commands = listCommands({ includeDisabled });
    return res.json({ commands, count: commands.length });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.post('/commands', (req, res) => {
  try {
    const { name, description, response_text, use_ai, tags, enabled } = req.body || {};
    if (!name || !String(name).trim()) {
      return res.status(400).json({ error: 'name is required' });
    }
    if (!response_text || !String(response_text).trim()) {
      return res.status(400).json({ error: 'response_text is required' });
    }
    const command = createCommand({
      name,
      description,
      responseText: response_text,
      useAi: Boolean(use_ai),
      tags,
      enabled: enabled !== false
    });
    return res.status(201).json({ command });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

router.put('/commands/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid command id' });
    }
    const payload = {
      name: req.body?.name,
      description: req.body?.description,
      responseText: req.body?.response_text,
      useAi: req.body?.use_ai,
      tags: req.body?.tags,
      enabled: req.body?.enabled
    };
    const command = updateCommand(id, payload);
    if (!command) {
      return res.status(404).json({ error: 'Command not found' });
    }
    return res.json({ command });
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

router.delete('/commands/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid command id' });
    }
    const existed = deleteCommand(id);
    if (!existed) {
      return res.status(404).json({ error: 'Command not found' });
    }
    return res.json({ deleted: true, id });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/training/documents', (req, res) => {
  try {
    const limit = Math.min(parseInt(req.query.limit || '50', 10), 200);
    const offset = parseInt(req.query.offset || '0', 10);
    const documents = listDocuments({ limit, offset });
    const stats = getKnowledgeStats();
    return res.json({
      documents,
      stats,
      limits: { maxDocumentBytes: MAX_DOCUMENT_BYTES }
    });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.get('/training/documents/:id/chunks', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid document id' });
    }
    const limit = Math.min(parseInt(req.query.limit || '200', 10), 500);
    const offset = parseInt(req.query.offset || '0', 10);
    const chunks = getDocumentChunks(id, { limit, offset });
    return res.json({ chunks, count: chunks.length });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

router.post('/training/documents', (req, res) => {
  try {
    const { title, source_type, content, tags } = req.body || {};
    if (!title || !String(title).trim()) {
      return res.status(400).json({ error: 'title is required' });
    }
    if (!content || !String(content).trim()) {
      return res.status(400).json({ error: 'content is required' });
    }
    if (Buffer.byteLength(String(content), 'utf8') > MAX_DOCUMENT_BYTES) {
      return res.status(413).json({ error: `content exceeds ${MAX_DOCUMENT_BYTES} bytes` });
    }
    const result = ingestDocument({
      title,
      sourceType: source_type,
      content,
      tags
    });
    return res.status(201).json(result);
  } catch (err) {
    return res.status(400).json({ error: err.message });
  }
});

router.delete('/training/documents/:id', (req, res) => {
  try {
    const id = parseInt(req.params.id, 10);
    if (!Number.isFinite(id)) {
      return res.status(400).json({ error: 'Invalid document id' });
    }
    const existed = deleteDocument(id);
    if (!existed) {
      return res.status(404).json({ error: 'Document not found' });
    }
    return res.json({ deleted: true, id });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

module.exports = router;

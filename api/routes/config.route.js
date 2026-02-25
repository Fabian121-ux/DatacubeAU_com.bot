'use strict';

const { Router } = require('express');
const { getAllConfig, setConfig } = require('../../utils/config-loader');
const { invalidateCache } = require('../../ai/context-injector');
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

router.get('/', (req, res) => {
  try {
    const config = getAllConfig();
    const filtered = Object.fromEntries(
      Object.entries(config).filter(([key]) => ALLOWED_CONFIG_KEYS.includes(key))
    );
    res.json({ config: filtered });
  } catch (err) {
    res.status(500).json({ error: err.message });
  }
});

router.put('/', (req, res) => {
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

router.post('/invalidate-context', (req, res) => {
  try {
    invalidateCache();
    return res.json({ message: 'Context cache invalidated - will reload on next AI call' });
  } catch (err) {
    return res.status(500).json({ error: err.message });
  }
});

module.exports = router;

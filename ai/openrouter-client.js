'use strict';

const axios = require('axios');
const logger = require('../utils/logger');
const { getBool, getConfig, getInt } = require('../utils/config-loader');
const { getTodayAiCallStats } = require('../db/ai-calls.db');

const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';
const FALLBACK_RESPONSE = "I couldn't answer that right now. Type HELP or contact admin.";

const circuit = {
  state: 'closed', // closed | open | half_open
  consecutiveFailures: 0,
  openedAt: 0
};

function estimateCost(promptTokens, completionTokens) {
  return promptTokens * 0.00000025 + completionTokens * 0.00000125;
}

function getCircuitSettings() {
  return {
    threshold: Math.max(2, getInt('openrouter_circuit_failure_threshold', 5)),
    cooldownMs: Math.max(15_000, getInt('openrouter_circuit_cooldown_ms', 90_000))
  };
}

function isCircuitOpen() {
  if (circuit.state !== 'open') return false;
  const { cooldownMs } = getCircuitSettings();
  const elapsed = Date.now() - circuit.openedAt;
  if (elapsed >= cooldownMs) {
    circuit.state = 'half_open';
    return false;
  }
  return true;
}

function onSuccess() {
  circuit.consecutiveFailures = 0;
  circuit.state = 'closed';
}

function onFailure(reason) {
  const { threshold } = getCircuitSettings();
  circuit.consecutiveFailures += 1;
  if (circuit.consecutiveFailures >= threshold) {
    circuit.state = 'open';
    circuit.openedAt = Date.now();
    logger.error(`OpenRouter circuit opened after ${circuit.consecutiveFailures} failures`, {
      reason
    });
  }
}

function shouldRetry(err) {
  const status = err.response?.status;
  if (!status) return true; // timeout/network
  return status === 408 || status === 409 || status === 429 || status >= 500;
}

async function callModelOnce({ apiKey, model, messages, maxTokens, timeoutMs }) {
  const response = await axios.post(
    `${OPENROUTER_BASE_URL}/chat/completions`,
    {
      model,
      messages,
      max_tokens: maxTokens,
      temperature: 0.2
    },
    {
      headers: {
        Authorization: `Bearer ${apiKey}`,
        'HTTP-Referer': 'https://datacube.au',
        'X-Title': 'Datacube AU Bot',
        'Content-Type': 'application/json'
      },
      timeout: timeoutMs
    }
  );

  const choice = response.data?.choices?.[0];
  const content = choice?.message?.content || FALLBACK_RESPONSE;
  const usage = response.data?.usage || {};
  const promptTokens = usage.prompt_tokens || 0;
  const completionTokens = usage.completion_tokens || 0;
  const costUsd = estimateCost(promptTokens, completionTokens);

  return {
    content,
    model,
    promptTokens,
    completionTokens,
    costUsd,
    success: true
  };
}

async function callModelWithRetry({ apiKey, model, messages, maxTokens, timeoutMs, retryOnce }) {
  try {
    return await callModelOnce({ apiKey, model, messages, maxTokens, timeoutMs });
  } catch (err) {
    if (!retryOnce || !shouldRetry(err)) {
      throw err;
    }
    logger.warn(`OpenRouter retrying once for model ${model}`);
    return callModelOnce({ apiKey, model, messages, maxTokens, timeoutMs });
  }
}

function budgetExceeded() {
  const dailyBudget = Number.parseFloat(
    getConfig('openrouter_budget_daily_usd', process.env.OPENROUTER_BUDGET_DAILY_USD || '2.00')
  );

  if (!Number.isFinite(dailyBudget) || dailyBudget <= 0) {
    return false;
  }

  const today = getTodayAiCallStats();
  const todayCost = Number(today?.total_cost_usd || 0);
  return todayCost >= dailyBudget;
}

async function callOpenRouter(messages, options = {}) {
  const apiKey = process.env.OPENROUTER_API_KEY;
  if (!apiKey) {
    logger.error('OPENROUTER_API_KEY not set');
    return {
      content: FALLBACK_RESPONSE,
      model: 'none',
      promptTokens: 0,
      completionTokens: 0,
      costUsd: 0,
      success: false
    };
  }

  if (budgetExceeded()) {
    return {
      content: 'AI is temporarily paused because today\'s budget cap was reached. Please try again tomorrow.',
      model: getConfig('openrouter_model', process.env.OPENROUTER_MODEL || 'anthropic/claude-3-haiku'),
      promptTokens: 0,
      completionTokens: 0,
      costUsd: 0,
      success: false
    };
  }

  if (isCircuitOpen()) {
    return {
      content: 'AI is temporarily unavailable due to upstream instability. Please retry shortly.',
      model: getConfig('openrouter_model', process.env.OPENROUTER_MODEL || 'anthropic/claude-3-haiku'),
      promptTokens: 0,
      completionTokens: 0,
      costUsd: 0,
      success: false
    };
  }

  const primaryModel =
    options.model ||
    getConfig('openrouter_model', process.env.OPENROUTER_MODEL || 'anthropic/claude-3-haiku');
  const fallbackModel =
    options.fallbackModel ||
    getConfig('openrouter_fallback_model', process.env.OPENROUTER_FALLBACK_MODEL || primaryModel);
  const maxTokens = getInt(
    'openrouter_max_tokens',
    parseInt(process.env.OPENROUTER_MAX_TOKENS || '600', 10)
  );
  const timeoutMs = getInt('openrouter_timeout_ms', 30_000);
  const retryOnce = getBool('openrouter_retry_once', true);

  try {
    const result = await callModelWithRetry({
      apiKey,
      model: primaryModel,
      messages,
      maxTokens,
      timeoutMs,
      retryOnce
    });
    onSuccess();
    logger.info(
      `OpenRouter call ok: model=${result.model}, tokens=${result.promptTokens}+${result.completionTokens}, cost=$${result.costUsd.toFixed(
        6
      )}`
    );
    return result;
  } catch (primaryErr) {
    const status = primaryErr.response?.status;
    const errMsg = primaryErr.response?.data?.error?.message || primaryErr.message;
    logger.error(`OpenRouter primary model failed: ${status} - ${errMsg}`);

    if (fallbackModel && fallbackModel !== primaryModel) {
      try {
        const fallbackResult = await callModelWithRetry({
          apiKey,
          model: fallbackModel,
          messages,
          maxTokens,
          timeoutMs,
          retryOnce
        });
        onSuccess();
        logger.info(`OpenRouter fallback model succeeded: ${fallbackModel}`);
        return fallbackResult;
      } catch (fallbackErr) {
        const fallbackStatus = fallbackErr.response?.status;
        const fallbackMsg = fallbackErr.response?.data?.error?.message || fallbackErr.message;
        onFailure(fallbackMsg);
        logger.error(`OpenRouter fallback model failed: ${fallbackStatus} - ${fallbackMsg}`);
      }
    } else {
      onFailure(errMsg);
    }
  }

  return {
    content: FALLBACK_RESPONSE,
    model: primaryModel,
    promptTokens: 0,
    completionTokens: 0,
    costUsd: 0,
    success: false
  };
}

module.exports = { callOpenRouter, FALLBACK_RESPONSE };


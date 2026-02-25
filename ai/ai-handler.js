'use strict';

const logger = require('../utils/logger');
const { buildPrompt } = require('./prompt-builder');
const { callOpenRouter, FALLBACK_RESPONSE } = require('./openrouter-client');
const { formatResponse } = require('./response-formatter');
const { logAiCall } = require('../db/ai-calls.db');
const { incrementAiCallCount } = require('../db/users.db');
const { recordAiCall } = require('../utils/rate-limiter');
const { logOutbound } = require('../utils/message-logger');
const { saveCacheAnswer } = require('../db/qa-cache.db');
const { sendQueued } = require('../utils/outbound-queue');
const { hasSensitiveContent } = require('../utils/text-normalizer');

/**
 * Handle an AI message request.
 * @param {object} sock
 * @param {{ jid: string, text: string, name?: string|null }} ctx
 * @returns {{ success: boolean, model: string, costUsd: number, response: string }}
 */
async function handleAiMessage(sock, { jid, text, numberId = null }) {
  logger.info(`AI handler triggered for ${jid}: "${text.slice(0, 60)}"`);

  try {
    await sock.sendPresenceUpdate('composing', jid);
  } catch (_) {
    // no-op
  }

  let aiResult = null;

  try {
    const messages = buildPrompt(text);
    aiResult = await callOpenRouter(messages);

    const formattedResponse = formatResponse(aiResult.content);
    const finalResponse = formattedResponse || FALLBACK_RESPONSE;

    await sendQueued(sock, jid, { text: finalResponse }, { source: 'ai', numberId });

    logAiCall({
      jid,
      model: aiResult.model,
      promptTokens: aiResult.promptTokens,
      completionTokens: aiResult.completionTokens,
      costUsd: aiResult.costUsd,
      success: aiResult.success
    });

    incrementAiCallCount(jid);
    recordAiCall(jid);
    logOutbound(jid, finalResponse, 'ai', { numberId, usedAi: true });

    if (aiResult.success && !hasSensitiveContent(text) && !hasSensitiveContent(finalResponse)) {
      saveCacheAnswer({
        question: text,
        answerText: finalResponse,
        source: 'ai',
        model: aiResult.model
      });
    }

    logger.info(
      `AI reply sent to ${jid} (${aiResult.promptTokens + aiResult.completionTokens} tokens)`
    );

    return {
      success: aiResult.success,
      model: aiResult.model,
      costUsd: aiResult.costUsd || 0,
      response: finalResponse
    };
  } catch (err) {
    logger.error(`AI handler error for ${jid}`, { err: err.message, stack: err.stack });

    await sendQueued(sock, jid, { text: FALLBACK_RESPONSE }, { source: 'ai:error', numberId });
    logOutbound(jid, FALLBACK_RESPONSE, 'ai:error', { numberId, usedAi: true });

    logAiCall({
      jid,
      model: aiResult?.model || 'unknown',
      promptTokens: 0,
      completionTokens: 0,
      costUsd: 0,
      success: false
    });

    return {
      success: false,
      model: aiResult?.model || 'unknown',
      costUsd: 0,
      response: FALLBACK_RESPONSE
    };
  } finally {
    try {
      await sock.sendPresenceUpdate('paused', jid);
    } catch (_) {
      // no-op
    }
  }
}

module.exports = { handleAiMessage };

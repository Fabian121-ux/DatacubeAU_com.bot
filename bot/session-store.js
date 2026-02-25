'use strict';

/**
 * Baileys auth state persistence using the built-in useMultiFileAuthState.
 * Stores session files to disk so the bot doesn't need to re-scan QR on restart.
 */

const { useMultiFileAuthState } = require('@whiskeysockets/baileys');
const path = require('path');
const fs = require('fs');
const logger = require('../utils/logger');

const SESSION_PATH = process.env.WA_SESSION_PATH || './session';

/**
 * Ensure session directory exists.
 */
function ensureSessionDir() {
  if (!fs.existsSync(SESSION_PATH)) {
    fs.mkdirSync(SESSION_PATH, { recursive: true });
    logger.info(`Session directory created: ${SESSION_PATH}`);
  }
}

/**
 * Load or create auth state for Baileys.
 * Returns { state, saveCreds } — pass state to makeWASocket.
 */
async function loadAuthState() {
  ensureSessionDir();
  const { state, saveCreds } = await useMultiFileAuthState(SESSION_PATH);
  logger.info('Auth state loaded from session store');
  return { state, saveCreds };
}

/**
 * Clear session (force re-scan on next start).
 */
function clearSession() {
  if (fs.existsSync(SESSION_PATH)) {
    fs.rmSync(SESSION_PATH, { recursive: true, force: true });
    logger.info('Session cleared — will require QR scan on next start');
  }
}

/**
 * Check if a session exists (i.e., previously authenticated).
 */
function hasSession() {
  if (!fs.existsSync(SESSION_PATH)) return false;
  const files = fs.readdirSync(SESSION_PATH);
  return files.length > 0;
}

module.exports = { loadAuthState, clearSession, hasSession, SESSION_PATH };

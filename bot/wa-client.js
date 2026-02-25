'use strict';

const fs = require('fs');
const path = require('path');
const {
  default: makeWASocket,
  DisconnectReason,
  fetchLatestBaileysVersion,
  Browsers,
  useMultiFileAuthState
} = require('@whiskeysockets/baileys');
const { Boom } = require('@hapi/boom');
const QRCode = require('qrcode');

const logger = require('../utils/logger');
const { logEvent } = require('../db/events.db');
const {
  listBotNumbers,
  getBotNumberById,
  updateBotNumberStatus
} = require('../db/bot-numbers.db');

const SESSION_BASE_PATH = process.env.WA_SESSION_PATH || './session';
const DEFAULT_NUMBER_ID = Number(process.env.WA_DEFAULT_NUMBER_ID || 0) || null;

const clients = new Map();
let messageHandler = null;

function ensureDir(dirPath) {
  if (!fs.existsSync(dirPath)) {
    fs.mkdirSync(dirPath, { recursive: true });
  }
}

function getSessionPath(numberId) {
  const safeId = String(numberId);
  return path.join(SESSION_BASE_PATH, safeId);
}

function hasSession(numberId) {
  const sessionPath = getSessionPath(numberId);
  if (!fs.existsSync(sessionPath)) return false;
  const files = fs.readdirSync(sessionPath);
  return files.length > 0;
}

function ensureClient(numberId) {
  const id = Number(numberId);
  if (clients.has(id)) return clients.get(id);

  const client = {
    numberId: id,
    sock: null,
    qrBase64: null,
    pairingCode: null,
    isConnected: false,
    isConnecting: false,
    lifecycleState: 'disconnected',
    reconnectAttempts: 0,
    lastSeen: null,
    lastConnectedAt: null,
    lastDisconnectReason: null,
    lastError: null,
    heartbeatAt: null,
    startTime: null,
    reconnectTimer: null,
    heartbeatTimer: null,
    stopRequested: false
  };

  clients.set(id, client);
  return client;
}

function clearReconnectTimer(client) {
  if (client.reconnectTimer) {
    clearTimeout(client.reconnectTimer);
    client.reconnectTimer = null;
  }
}

function clearHeartbeat(client) {
  if (client.heartbeatTimer) {
    clearInterval(client.heartbeatTimer);
    client.heartbeatTimer = null;
  }
}

function startHeartbeat(client) {
  clearHeartbeat(client);
  client.heartbeatAt = new Date().toISOString();
  client.heartbeatTimer = setInterval(() => {
    if (!client.isConnected) return;
    client.heartbeatAt = new Date().toISOString();
  }, 15000);
}

function safeUpdateNumberStatus(numberId, status, options = {}) {
  try {
    updateBotNumberStatus(numberId, status, options);
  } catch (err) {
    logger.warn(`Failed to update bot_numbers status for ${numberId}`, { err: err.message });
  }
}

function mapDisconnectReason(statusCode) {
  if (statusCode === DisconnectReason.loggedOut) return 'logged_out';
  if (statusCode === DisconnectReason.connectionClosed) return 'connection_closed';
  if (statusCode === DisconnectReason.connectionLost) return 'connection_lost';
  if (statusCode === DisconnectReason.connectionReplaced) return 'connection_replaced';
  if (statusCode === DisconnectReason.restartRequired) return 'restart_required';
  if (statusCode === DisconnectReason.timedOut) return 'timed_out';
  if (statusCode === DisconnectReason.badSession) return 'bad_session';
  if (statusCode === DisconnectReason.multideviceMismatch) return 'multidevice_mismatch';
  return 'unknown';
}

function getLifecycleState(client) {
  if (client.isConnected) return 'connected';
  if (client.isConnecting && client.qrBase64) return 'waiting_qr';
  if (client.isConnecting) return 'booting';
  return client.lifecycleState || 'disconnected';
}

function toPublicState(client) {
  return {
    numberId: client.numberId,
    ready: client.isConnected,
    isConnected: client.isConnected,
    isConnecting: client.isConnecting,
    hasQR: Boolean(client.qrBase64),
    qrAvailable: Boolean(client.qrBase64),
    state: getLifecycleState(client),
    authState: getLifecycleState(client),
    uptime: client.startTime ? Math.floor((Date.now() - client.startTime) / 1000) : 0,
    reconnectAttempts: client.reconnectAttempts,
    lastSeen: client.lastSeen,
    hasSession: hasSession(client.numberId),
    lastConnectedAt: client.lastConnectedAt,
    lastDisconnectReason: client.lastDisconnectReason,
    lastError: client.lastError,
    heartbeatAt: client.heartbeatAt,
    pairingCodeAvailable: Boolean(client.pairingCode),
    pairingCode: client.pairingCode || null
  };
}

async function shutdownSocket(client) {
  if (!client.sock) return;
  try {
    if (typeof client.sock.end === 'function') {
      client.sock.end();
    }
  } catch (err) {
    logger.warn(`Failed to close WA socket for number ${client.numberId}`, { err: err.message });
  }
  client.sock = null;
}

async function startNumberClient(numberId, options = {}) {
  const { force = false } = options;
  const id = Number(numberId);
  const number = getBotNumberById(id);
  if (!number) {
    throw new Error(`Number ${id} not found`);
  }

  const client = ensureClient(id);

  if (client.isConnecting && !force) {
    return toPublicState(client);
  }

  if (force) {
    await shutdownSocket(client);
  }

  clearReconnectTimer(client);
  client.stopRequested = false;
  client.isConnecting = true;
  client.isConnected = false;
  client.lifecycleState = 'booting';
  client.qrBase64 = null;
  client.pairingCode = null;
  client.lastError = null;

  safeUpdateNumberStatus(id, 'pairing', {
    lastConnectedAt: number.last_connected_at || null
  });

  logEvent({
    eventType: 'wa_state',
    stage: 'boot',
    topic: 'pairing',
    detail: `number:${id}`
  });

  try {
    const { version } = await fetchLatestBaileysVersion();
    const sessionPath = getSessionPath(id);
    ensureDir(sessionPath);

    const { state: authState, saveCreds } = await useMultiFileAuthState(sessionPath);
    const sock = makeWASocket({
      version,
      auth: authState,
      printQRInTerminal: false,
      browser: Browsers.ubuntu('Chrome'),
      logger: require('pino')({ level: 'silent' }),
      generateHighQualityLinkPreview: false,
      syncFullHistory: false,
      markOnlineOnConnect: false
    });

    client.sock = sock;

    sock.ev.on('creds.update', saveCreds);

    sock.ev.on('connection.update', async (update) => {
      const { connection, lastDisconnect, qr } = update;

      if (qr) {
        try {
          client.qrBase64 = await QRCode.toDataURL(qr);
          client.lifecycleState = 'waiting_qr';
          client.isConnecting = true;
          safeUpdateNumberStatus(id, 'pairing', {
            lastConnectedAt: client.lastConnectedAt
          });
        } catch (err) {
          client.lastError = `qr_generation_failed:${err.message}`;
          client.qrBase64 = null;
        }
      }

      if (connection === 'open') {
        client.isConnected = true;
        client.isConnecting = false;
        client.lifecycleState = 'connected';
        client.qrBase64 = null;
        client.pairingCode = null;
        client.lastDisconnectReason = null;
        client.lastError = null;
        client.reconnectAttempts = 0;
        client.startTime = Date.now();
        client.lastSeen = new Date().toISOString();
        client.lastConnectedAt = client.lastSeen;
        startHeartbeat(client);

        safeUpdateNumberStatus(id, 'connected', {
          lastConnectedAt: Date.now()
        });

        logEvent({
          eventType: 'wa_state',
          stage: 'connection',
          topic: 'connected',
          detail: `number:${id}`
        });
      }

      if (connection === 'close') {
        client.isConnected = false;
        client.isConnecting = false;
        client.qrBase64 = null;
        client.lastSeen = new Date().toISOString();
        clearHeartbeat(client);

        const statusCode =
          lastDisconnect?.error instanceof Boom
            ? lastDisconnect.error.output?.statusCode
            : null;
        const reason = mapDisconnectReason(statusCode);
        client.lastDisconnectReason = reason;
        client.lastError = lastDisconnect?.error?.message || 'Connection Failure';
        client.lifecycleState = 'disconnected';

        const shouldReconnect = !client.stopRequested && statusCode !== DisconnectReason.loggedOut;

        if (shouldReconnect) {
          client.reconnectAttempts += 1;
          const delay = Math.min(5000 * client.reconnectAttempts, 60000);
          safeUpdateNumberStatus(id, 'pairing', {
            lastConnectedAt: client.lastConnectedAt ? Date.parse(client.lastConnectedAt) : null
          });
          client.reconnectTimer = setTimeout(() => {
            startNumberClient(id, { force: true }).catch((err) => {
              client.lastError = err.message;
              client.lifecycleState = 'disconnected';
            });
          }, delay);
        } else {
          safeUpdateNumberStatus(id, 'disconnected', {
            lastConnectedAt: client.lastConnectedAt ? Date.parse(client.lastConnectedAt) : null
          });
        }
      }
    });

    sock.ev.on('messages.upsert', async ({ messages, type }) => {
      if (type !== 'notify') return;
      if (!messageHandler) return;
      for (const msg of messages) {
        try {
          await messageHandler(sock, msg, { numberId: id });
        } catch (err) {
          logger.error('Error in number-scoped message handler', {
            err: err.message,
            stack: err.stack,
            numberId: id
          });
        }
      }
    });

    return toPublicState(client);
  } catch (err) {
    client.isConnecting = false;
    client.lifecycleState = 'disconnected';
    client.lastError = err.message;
    safeUpdateNumberStatus(id, 'disconnected', {
      lastConnectedAt: client.lastConnectedAt ? Date.parse(client.lastConnectedAt) : null
    });
    throw err;
  }
}

async function disconnectNumber(numberId, options = {}) {
  const { clearSession = true } = options;
  const id = Number(numberId);
  const number = getBotNumberById(id);
  if (!number) {
    throw new Error(`Number ${id} not found`);
  }

  const client = ensureClient(id);
  client.stopRequested = true;
  clearReconnectTimer(client);
  clearHeartbeat(client);
  await shutdownSocket(client);

  client.isConnected = false;
  client.isConnecting = false;
  client.qrBase64 = null;
  client.pairingCode = null;
  client.lifecycleState = 'disconnected';

  if (clearSession) {
    const sessionPath = getSessionPath(id);
    if (fs.existsSync(sessionPath)) {
      fs.rmSync(sessionPath, { recursive: true, force: true });
    }
  }

  safeUpdateNumberStatus(id, 'disconnected', {
    lastConnectedAt: client.lastConnectedAt ? Date.parse(client.lastConnectedAt) : null
  });

  return toPublicState(client);
}

function resolveDefaultNumberId() {
  if (DEFAULT_NUMBER_ID && getBotNumberById(DEFAULT_NUMBER_ID)) {
    return DEFAULT_NUMBER_ID;
  }

  for (const [id, client] of clients.entries()) {
    if (client.isConnected || client.isConnecting) {
      return id;
    }
  }

  const allNumbers = listBotNumbers();
  return allNumbers.length > 0 ? Number(allNumbers[0].id) : null;
}

function getClientStateByNumber(numberId) {
  const id = Number(numberId);
  const existing = clients.get(id);
  if (existing) return toPublicState(existing);

  const number = getBotNumberById(id);
  if (!number) return null;

  const stateFromDb = number.status === 'connected'
    ? 'connected'
    : number.status === 'pairing'
      ? 'waiting_qr'
      : 'disconnected';

  return {
    numberId: id,
    ready: false,
    isConnected: false,
    isConnecting: false,
    hasQR: false,
    qrAvailable: false,
    state: stateFromDb,
    authState: stateFromDb,
    uptime: 0,
    reconnectAttempts: 0,
    lastSeen: null,
    hasSession: hasSession(id),
    lastConnectedAt: number.last_connected_at
      ? new Date(Number(number.last_connected_at)).toISOString()
      : null,
    lastDisconnectReason: null,
    lastError: null,
    heartbeatAt: null,
    pairingCodeAvailable: false,
    pairingCode: null
  };
}

function getBotState(numberId = null) {
  const id = numberId === null || numberId === undefined
    ? resolveDefaultNumberId()
    : Number(numberId);

  if (!id) {
    return {
      numberId: null,
      ready: false,
      isConnected: false,
      isConnecting: false,
      hasQR: false,
      qrAvailable: false,
      state: 'disconnected',
      authState: 'disconnected',
      uptime: 0,
      reconnectAttempts: 0,
      lastSeen: null,
      hasSession: false,
      lastConnectedAt: null,
      lastDisconnectReason: null,
      lastError: null,
      heartbeatAt: null,
      pairingCodeAvailable: false,
      pairingCode: null
    };
  }

  return getClientStateByNumber(id);
}

function getQRCode(numberId = null) {
  const id = numberId === null || numberId === undefined
    ? resolveDefaultNumberId()
    : Number(numberId);
  if (!id) return null;
  const client = clients.get(id);
  return client?.qrBase64 || null;
}

function getSock(numberId = null) {
  const id = numberId === null || numberId === undefined
    ? resolveDefaultNumberId()
    : Number(numberId);
  if (!id) return null;
  const client = clients.get(id);
  return client?.sock || null;
}

function getAllBotStates() {
  const numbers = listBotNumbers();
  return numbers.map((number) => getClientStateByNumber(number.id));
}

async function pairNumber(numberId) {
  const id = Number(numberId);
  const number = getBotNumberById(id);
  if (!number) {
    throw new Error(`Number ${id} not found`);
  }

  safeUpdateNumberStatus(id, 'pairing', {
    lastConnectedAt: number.last_connected_at || null
  });
  return startNumberClient(id, { force: true });
}

async function reconnectClient(numberId = null) {
  const id = numberId === null || numberId === undefined
    ? resolveDefaultNumberId()
    : Number(numberId);

  if (!id) {
    throw new Error('No WhatsApp number is configured');
  }

  return pairNumber(id);
}

function normalizePhoneNumber(phoneNumber, options = {}) {
  const raw = String(phoneNumber || '').trim();
  if (!raw) {
    throw new Error('phoneNumber is required');
  }

  let digits = raw.replace(/\D/g, '');
  if (!digits) {
    throw new Error('phoneNumber must contain digits');
  }

  if (digits.startsWith('00')) {
    digits = digits.slice(2);
  }

  const fallbackCountryCode = String(process.env.WA_DEFAULT_COUNTRY_CODE || '').replace(/\D/g, '');
  const countryCode = String(options.countryCode || fallbackCountryCode || '').replace(/\D/g, '');
  if (digits.startsWith('0')) {
    if (!countryCode) {
      throw new Error('phoneNumber must include country code');
    }
    digits = `${countryCode}${digits.slice(1)}`;
  }

  if (digits.length < 8 || digits.length > 15) {
    throw new Error('phoneNumber must be 8-15 digits');
  }

  return digits;
}

async function requestPairingCode(phoneNumber, options = {}) {
  const id = options.numberId !== undefined && options.numberId !== null
    ? Number(options.numberId)
    : resolveDefaultNumberId();
  if (!id) {
    throw new Error('No WhatsApp number is configured');
  }

  const normalizedPhone = normalizePhoneNumber(phoneNumber, options);
  const client = ensureClient(id);

  if (!client.sock) {
    await startNumberClient(id, { force: true });
  }

  if (!client.sock || typeof client.sock.requestPairingCode !== 'function') {
    throw new Error('WhatsApp socket is not ready for pairing code requests');
  }

  const pairingCode = await client.sock.requestPairingCode(normalizedPhone, options.customPairingCode);
  client.pairingCode = pairingCode;
  return {
    numberId: id,
    phoneNumber: normalizedPhone,
    pairingCode,
    createdAt: new Date().toISOString()
  };
}

async function startClient(options = {}) {
  if (options.numberId !== undefined && options.numberId !== null) {
    return startNumberClient(Number(options.numberId), { force: Boolean(options.force) });
  }

  const numbers = listBotNumbers();
  const candidates = numbers.filter((number) => ['pairing', 'connected'].includes(number.status));

  for (const number of candidates) {
    startNumberClient(number.id, { force: true }).catch((err) => {
      const client = ensureClient(number.id);
      client.lastError = err.message;
      client.lifecycleState = 'disconnected';
    });
  }

  return getAllBotStates();
}

async function stopClient() {
  const entries = Array.from(clients.entries());
  for (const [id, client] of entries) {
    client.stopRequested = true;
    clearReconnectTimer(client);
    clearHeartbeat(client);
    await shutdownSocket(client);

    client.isConnected = false;
    client.isConnecting = false;
    client.qrBase64 = null;
    client.lifecycleState = 'disconnected';

    // Keep DB status unchanged on process shutdown so reconnect-on-restart can work.
    logger.info(`Stopped WA client for number ${id}`);
  }
}

function setMessageHandler(handler) {
  messageHandler = handler;
}

module.exports = {
  startClient,
  stopClient,
  setMessageHandler,
  getBotState,
  getAllBotStates,
  getQRCode,
  getSock,
  pairNumber,
  reconnectClient,
  disconnectNumber,
  requestPairingCode,
  startNumberClient,
  getClientStateByNumber
};

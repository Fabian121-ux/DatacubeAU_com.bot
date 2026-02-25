'use strict';

const { Router } = require('express');
const {
  getBotState,
  getClientStateByNumber,
  getQRCode,
  pairNumber,
  reconnectClient,
  disconnectNumber,
  requestPairingCode
} = require('../../bot/wa-client');
const { getBotNumberById } = require('../../db/bot-numbers.db');

const router = Router();

function normalizeNumberId(value) {
  const id = Number(value);
  if (!Number.isFinite(id) || id <= 0) {
    return null;
  }
  return id;
}

function toPayload(state) {
  if (!state) return null;
  return {
    numberId: state.numberId ?? null,
    ready: Boolean(state.ready || state.isConnected),
    hasQR: Boolean(state.hasQR || state.qrAvailable),
    state: state.state || state.authState || 'disconnected',
    authState: state.authState || state.state || 'disconnected',
    lastSeen: state.lastSeen || null,
    lastConnectedAt: state.lastConnectedAt || null,
    lastDisconnectReason: state.lastDisconnectReason || null,
    lastError: state.lastError || null,
    heartbeatAt: state.heartbeatAt || null,
    hasSession: Boolean(state.hasSession),
    reconnectAttempts: Number(state.reconnectAttempts || 0),
    uptime: Number(state.uptime || 0)
  };
}

function sendQrPng(res, qrDataUrl) {
  const base64Payload = qrDataUrl.includes(',') ? qrDataUrl.split(',')[1] : qrDataUrl;
  const buffer = Buffer.from(base64Payload, 'base64');
  res.setHeader('Content-Type', 'image/png');
  res.setHeader('Cache-Control', 'no-store');
  return res.send(buffer);
}

router.get('/status', (req, res) => {
  return res.json(toPayload(getBotState()));
});

router.get('/status/:numberId', (req, res) => {
  const numberId = normalizeNumberId(req.params.numberId);
  if (!numberId) {
    return res.status(400).json({ error: 'invalid numberId' });
  }

  const state = getClientStateByNumber(numberId);
  if (!state) {
    return res.status(404).json({ error: 'number not found' });
  }

  return res.json(toPayload(state));
});

router.get('/qr', (req, res) => {
  const qrDataUrl = getQRCode();
  const format = (req.query.format || '').toString().toLowerCase();
  if (format === 'json') {
    const state = toPayload(getBotState());
    return res.json({
      ...state,
      qr: qrDataUrl || null
    });
  }
  if (!qrDataUrl) {
    return res.status(404).json({ error: 'QR not available' });
  }
  return sendQrPng(res, qrDataUrl);
});

router.get('/qr/:numberId', (req, res) => {
  const numberId = normalizeNumberId(req.params.numberId);
  if (!numberId) {
    return res.status(400).json({ error: 'invalid numberId' });
  }

  const state = getClientStateByNumber(numberId);
  if (!state) {
    return res.status(404).json({ error: 'number not found' });
  }

  const qrDataUrl = getQRCode(numberId);
  const format = (req.query.format || '').toString().toLowerCase();
  if (format === 'json') {
    return res.json({
      ...toPayload(state),
      qr: qrDataUrl || null
    });
  }
  if (!qrDataUrl) {
    return res.status(404).json({ error: 'QR not available' });
  }

  return sendQrPng(res, qrDataUrl);
});

router.post('/pair/:numberId', async (req, res) => {
  const numberId = normalizeNumberId(req.params.numberId);
  if (!numberId) {
    return res.status(400).json({ error: 'invalid numberId' });
  }
  if (!getBotNumberById(numberId)) {
    return res.status(404).json({ error: 'number not found' });
  }

  try {
    const state = await pairNumber(numberId);
    return res.json({ message: 'Pairing started', state: toPayload(state) });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'failed to pair number' });
  }
});

router.post('/disconnect/:numberId', async (req, res) => {
  const numberId = normalizeNumberId(req.params.numberId);
  if (!numberId) {
    return res.status(400).json({ error: 'invalid numberId' });
  }
  if (!getBotNumberById(numberId)) {
    return res.status(404).json({ error: 'number not found' });
  }

  try {
    const state = await disconnectNumber(numberId, { clearSession: true });
    return res.json({ message: 'Number disconnected', state: toPayload(state) });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'failed to disconnect number' });
  }
});

router.post('/reconnect', async (req, res) => {
  try {
    const before = toPayload(getBotState());
    const next = await reconnectClient();
    return res.json({
      message: 'Reconnect requested',
      before,
      after: toPayload(next)
    });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'failed to reconnect' });
  }
});

router.post('/pairing-code', async (req, res) => {
  try {
    const phoneNumber = req.body?.phoneNumber;
    const countryCode = req.body?.countryCode;
    const numberId = req.body?.numberId;
    const customPairingCode = req.body?.customPairingCode;

    if (!phoneNumber) {
      return res.status(400).json({ error: 'phoneNumber is required' });
    }

    const result = await requestPairingCode(phoneNumber, {
      countryCode,
      numberId,
      customPairingCode
    });

    return res.json({
      message: 'Pairing code generated',
      numberId: result.numberId,
      phoneNumber: result.phoneNumber,
      pairingCode: result.pairingCode,
      createdAt: result.createdAt,
      state: toPayload(getBotState(result.numberId))
    });
  } catch (err) {
    return res.status(500).json({ error: err.message || 'failed to generate pairing code' });
  }
});

module.exports = router;

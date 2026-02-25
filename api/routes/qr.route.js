'use strict';

const { Router } = require('express');
const { getQRCode, getBotState } = require('../../bot/wa-client');

const router = Router();

router.get('/', (req, res) => {
  const state = getBotState();
  const qr = getQRCode();
  const lifecycleState = state.state || state.lifecycleState || state.authState || 'booting';

  if (state.ready || state.isConnected) {
    return res.json({
      state: 'connected',
      status: 'connected',
      qr: null,
      message: 'Bot is connected'
    });
  }

  if (qr) {
    return res.json({
      state: 'waiting_qr',
      status: 'waiting_qr',
      qr,
      message: 'Scan this QR code with WhatsApp'
    });
  }

  if (state.isConnecting) {
    return res.json({
      state: 'booting',
      status: 'booting',
      qr: null,
      message: 'Pairing in progress'
    });
  }

  return res.json({
    state: lifecycleState,
    status: lifecycleState,
    qr: null,
    message: state.lastError ? `Bot is disconnected: ${state.lastError}` : 'Bot is disconnected'
  });
});

module.exports = router;

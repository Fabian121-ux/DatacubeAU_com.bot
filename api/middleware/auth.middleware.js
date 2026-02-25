'use strict';

const logger = require('../../utils/logger');

function authMiddleware(req, res, next) {
  const adminToken =
    process.env.ADMIN_TOKEN || process.env.ADMIN_API_TOKEN || process.env.API_SECRET_KEY;

  if (!adminToken) {
    logger.error('ADMIN_TOKEN not configured; API requests will be rejected');
    return res.status(500).json({ error: 'Server misconfiguration: auth token not set' });
  }

  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    const token = authHeader.slice(7);
    if (token === adminToken) return next();
  }

  const apiKey = req.headers['x-api-key'];
  if (apiKey && apiKey === adminToken) return next();

  logger.warn(`Unauthorized API request: ${req.method} ${req.path} from ${req.ip}`);
  return res.status(401).json({ error: 'Unauthorized: invalid or missing token' });
}

module.exports = authMiddleware;


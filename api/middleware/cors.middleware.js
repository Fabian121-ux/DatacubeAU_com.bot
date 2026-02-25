'use strict';

const cors = require('cors');

/**
 * CORS middleware — restricted to admin panel origin.
 * In development, allows localhost:3000.
 * In production, allows NEXTAUTH_URL or ADMIN_ORIGIN env var.
 */

function getCorsOptions() {
  const isDev = process.env.NODE_ENV !== 'production';

  const allowedOrigins = [
    'http://localhost:3000',
    'http://localhost:3001',
    process.env.NEXTAUTH_URL,
    process.env.ADMIN_ORIGIN
  ].filter(Boolean);

  return {
    origin: (origin, callback) => {
      // Allow requests with no origin (curl, Postman, server-to-server)
      if (!origin) return callback(null, true);

      if (isDev || allowedOrigins.includes(origin)) {
        return callback(null, true);
      }

      return callback(new Error(`CORS: Origin ${origin} not allowed`));
    },
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-API-Key'],
    credentials: true
  };
}

module.exports = cors(getCorsOptions());

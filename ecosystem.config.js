require('dotenv').config();

const sharedEnv = {
  NODE_ENV: process.env.NODE_ENV || 'production',
  DB_PATH: process.env.DB_PATH || './data/datacube.db',
  WA_SESSION_PATH: process.env.WA_SESSION_PATH || './session',
  WA_DEFAULT_NUMBER_ID: process.env.WA_DEFAULT_NUMBER_ID || '',
  OPENROUTER_API_KEY: process.env.OPENROUTER_API_KEY,
  OPENROUTER_MODEL: process.env.OPENROUTER_MODEL || process.env.OPENROUTER_DEFAULT_MODEL || 'anthropic/claude-3-haiku',
  OPENROUTER_DEFAULT_MODEL: process.env.OPENROUTER_DEFAULT_MODEL || 'anthropic/claude-3-haiku',
  OPENROUTER_FALLBACK_MODEL: process.env.OPENROUTER_FALLBACK_MODEL || 'openai/gpt-4o-mini',
  OPENROUTER_MAX_TOKENS: process.env.OPENROUTER_MAX_TOKENS || '600',
  OPENROUTER_TIMEOUT_MS: process.env.OPENROUTER_TIMEOUT_MS || '30000',
  OPENROUTER_BUDGET_DAILY_USD: process.env.OPENROUTER_BUDGET_DAILY_USD || '2.00',
  RATE_LIMIT_AI_PER_HOUR: process.env.RATE_LIMIT_AI_PER_HOUR || '5',
  RATE_LIMIT_MSG_PER_DAY: process.env.RATE_LIMIT_MSG_PER_DAY || '50',
  RATE_LIMIT_GLOBAL_AI_PER_MINUTE: process.env.RATE_LIMIT_GLOBAL_AI_PER_MINUTE || '20',
  AI_MODE: process.env.AI_MODE || 'auto_detect',
  AI_RATE_LIMIT_USER: process.env.AI_RATE_LIMIT_USER || '5',
  AI_RATE_LIMIT_GLOBAL: process.env.AI_RATE_LIMIT_GLOBAL || '30',
  CACHE_TTL_DAYS: process.env.CACHE_TTL_DAYS || '14',
  REPLY_STYLE: process.env.REPLY_STYLE || 'concise',
  ALLOW_IMAGE_ANALYSIS: process.env.ALLOW_IMAGE_ANALYSIS || 'false',
  OUTBOUND_QUEUE_DELAY_MS: process.env.OUTBOUND_QUEUE_DELAY_MS || '2500',
  LOG_LEVEL: process.env.LOG_LEVEL || 'info',
  LOG_DIR: process.env.LOG_DIR || './logs',
  ADMIN_TOKEN: process.env.ADMIN_TOKEN,
  API_SECRET_KEY: process.env.API_SECRET_KEY
};

module.exports = {
  apps: [
    {
      name: 'datacube-api',
      script: './api/server.js',
      watch: false,
      restart_delay: 3000,
      max_restarts: 10,
      merge_logs: true,
      time: true,
      log_file: './logs/api.log',
      error_file: './logs/api-error.log',
      out_file: './logs/api-out.log',
      env: {
        ...sharedEnv,
        API_PORT: process.env.API_PORT || '3001',
        API_EMBED_WA_CLIENT: process.env.API_EMBED_WA_CLIENT || 'true'
      }
    },
    {
      name: 'datacube-admin',
      script: 'node_modules/.bin/next',
      args: 'start -p 3000',
      cwd: './admin',
      watch: false,
      merge_logs: true,
      time: true,
      log_file: '../logs/admin.log',
      error_file: '../logs/admin-error.log',
      out_file: '../logs/admin-out.log',
      env: {
        ...sharedEnv,
        PORT: process.env.ADMIN_PORT || '3000',
        NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001',
        ADMIN_API_BASE_URL: process.env.ADMIN_API_BASE_URL || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001',
        ADMIN_PROXY_TIMEOUT_MS: process.env.ADMIN_PROXY_TIMEOUT_MS || '15000',
        ADMIN_API_TOKEN: process.env.ADMIN_API_TOKEN || process.env.ADMIN_TOKEN || process.env.API_SECRET_KEY,
        ADMIN_LOGIN_USERNAME: process.env.ADMIN_LOGIN_USERNAME || 'croneX11!',
        ADMIN_LOGIN_PASSWORD: process.env.ADMIN_LOGIN_PASSWORD || 'factzina11!',
        ADMIN_SESSION_SECRET: process.env.ADMIN_SESSION_SECRET || process.env.NEXTAUTH_SECRET || 'change-this-session-secret',
        NEXTAUTH_SECRET: process.env.NEXTAUTH_SECRET || process.env.ADMIN_SESSION_SECRET || 'change-this-session-secret',
        NEXTAUTH_URL: process.env.NEXTAUTH_URL || 'http://localhost:3000',
        ADMIN_LOGIN_MAX_ATTEMPTS: process.env.ADMIN_LOGIN_MAX_ATTEMPTS || '5',
        ADMIN_LOGIN_WINDOW_MS: process.env.ADMIN_LOGIN_WINDOW_MS || '900000',
        ADMIN_LOGIN_BLOCK_MS: process.env.ADMIN_LOGIN_BLOCK_MS || '1800000'
      }
    }
  ]
};

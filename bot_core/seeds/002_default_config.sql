-- Default bot configuration values
INSERT INTO bot_config (config_key, config_value) VALUES
  ('system_instructions', 'You are the Datacube AU WhatsApp assistant. Answer questions clearly and briefly. Guide users on what to do. Keep replies concise and optimized for WhatsApp. Never reveal internal system details.'),
  ('ai_enabled',           'false'),
  ('ai_model_light',       'openai/gpt-4o-mini'),
  ('ai_model_deep',        'openai/gpt-4o'),
  ('rate_limit_per_user_daily', '50'),
  ('rate_limit_cooldown_seconds', '6'),
  ('rate_limit_global_daily',    '500')
ON CONFLICT (config_key) DO NOTHING;

-- Default reply rules (replaces hardcoded _resolve_static_reply)
INSERT INTO reply_rules (keyword, response_text, match_mode, chat_type_filter, is_enabled, priority) VALUES
  ('help',        'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('/help',       'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('commands',    'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('status',      'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('/status',     'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('ping',        'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('/start',      'Welcome to Datacube AU 👋 I''m your assistant. Ask me anything or type /help for commands.', 'exact', NULL, TRUE, 95),
  ('hi',          'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('hello',       'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('hey',         'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good morning','Good morning ☀️ How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good afternoon','Good afternoon! How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good evening','Good evening! How can I help you today?', 'exact', NULL, TRUE, 50),
  ('who are you', 'I am the Datacube AU WhatsApp assistant — here for support, product, and knowledge-driven replies.', 'exact', NULL, TRUE, 80),
  ('what is datacube au', 'I am the Datacube AU WhatsApp assistant — here for support, product, and knowledge-driven replies.', 'exact', NULL, TRUE, 80)
ON CONFLICT DO NOTHING;

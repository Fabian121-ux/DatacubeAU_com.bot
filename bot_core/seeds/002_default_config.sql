-- Default bot configuration values
INSERT INTO bot_config (config_key, config_value) VALUES
  ('system_instructions', 'Generated automatically from the assistant identity/profile settings.'),
  ('ai_enabled',           'false'),
  ('ai_model_light',       'openai/gpt-4o-mini'),
  ('ai_model_deep',        'openai/gpt-4o'),
  ('rate_limit_per_user_daily', '50'),
  ('rate_limit_cooldown_seconds', '6'),
  ('rate_limit_global_daily',    '500'),
  ('assistant_name',       'Zina'),
  ('assistant_role',       'Fabian''s Personal AI Assistant'),
  ('owner_name',           'Fabian'),
  ('owner_bio',            'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.'),
  ('identity_bio',         'Fabian is a developer, AI systems builder, automation-focused creator, and productivity and cybersecurity enthusiast.'),
  ('identity_projects',    'AI systems, automation tools, WhatsApp assistant systems, knowledge and productivity projects. Main active project: Datacube AU.'),
  ('identity_services',    'AI-assisted systems, automation tools, and productivity-focused projects.'),
  ('identity_skills',      'AI, Automation, Cybersecurity, Python, Node.js'),
  ('identity_interests',   'Technology, Productivity, Automation'),
  ('identity_focus',       'Building intelligent WhatsApp assistants'),
  ('identity_style',       'Helpful, concise, and direct')
ON CONFLICT (config_key) DO NOTHING;

-- Default reply rules (replaces hardcoded _resolve_static_reply)
INSERT INTO reply_rules (keyword, response_text, match_mode, chat_type_filter, is_enabled, priority) VALUES
  ('help',        'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('/help',       'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('commands',    'Available commands: /help, /status, /mode. Mention the bot in groups to trigger a reply.', 'exact', NULL, TRUE, 100),
  ('status',      'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('/status',     'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('ping',        'Datacube AU bot status: online ✅ Knowledge search is enabled.', 'exact', NULL, TRUE, 90),
  ('/start',      'Welcome to Datacube AU 👋 I''m Zina, Fabian''s AI assistant. Ask me anything or type /help for commands.', 'exact', NULL, TRUE, 95),
  ('hi',          'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('hello',       'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('hey',         'Hello 👋 How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good morning','Good morning ☀️ How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good afternoon','Good afternoon! How can I help you today?', 'exact', NULL, TRUE, 50),
  ('good evening','Good evening! How can I help you today?', 'exact', NULL, TRUE, 50),
  ('who are you', 'Hi 👋 I''m Zina, Fabian''s AI assistant. I help answer questions about Fabian, his projects, and Datacube AU.', 'exact', NULL, TRUE, 80),
  ('what is your name', 'Hi 👋 I''m Zina, Fabian''s AI assistant. I help answer questions about Fabian, his projects, and Datacube AU.', 'exact', NULL, TRUE, 80),
  ('what is datacube au', 'Datacube AU is Fabian''s intelligent WhatsApp assistant system for smart replies, memory, automation, and AI-assisted interactions.', 'exact', NULL, TRUE, 80)
ON CONFLICT DO NOTHING;

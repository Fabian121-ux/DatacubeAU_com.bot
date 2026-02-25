# Datacube AU — Frequently Asked Questions

## General

**Q: What is Datacube AU?**
A: Datacube AU is a developer platform and community focused on modern web architecture, AI integration, and cloud-native development. We provide tools, documentation, and community support for developers.

**Q: How do I get started with Datacube AU?**
A: Visit https://datacube.au, create an account, and explore the documentation at https://docs.datacube.au.

**Q: What programming languages does Datacube AU support?**
A: Primarily JavaScript/TypeScript (Node.js, Next.js), but the platform is language-agnostic for API integrations.

## WhatsApp Bot

**Q: How do I enable AI replies?**
A: Send `START` to opt in. The bot will then answer your programming and tech questions.

**Q: What topics can the bot answer?**
A: Programming questions, architecture guidance, Datacube AU platform questions, debugging help, and general tech questions.

**Q: Why isn't the bot responding to my question?**
A: Make sure you've sent `START` to opt in. Also check that your question is tech-related. Type `!help` for commands.

**Q: How many AI questions can I ask?**
A: Up to 5 AI replies per hour per user. This limit resets every hour.

## Technical

**Q: How does Datacube AU use Qdrant?**
A: Qdrant is used as a vector database for RAG (Retrieval-Augmented Generation). Documents are chunked, embedded using OpenAI embeddings, and stored in Qdrant. When a user asks a question, relevant chunks are retrieved and injected into the AI prompt for context-aware answers.

**Q: What is the difference between Supabase and SQLite in the stack?**
A: Supabase (PostgreSQL) is used for the main application database — user data, content, etc. SQLite is used locally for the WhatsApp bot to store message logs, rate limits, and config without needing a separate database server.

**Q: How does the bot handle rate limiting?**
A: Per-user: 5 AI replies/hour, 50 messages/day. Global: 20 AI calls/minute. Rate limits are stored in SQLite and checked before each AI call.

**Q: How is the WhatsApp session persisted?**
A: Baileys saves auth state to disk using `useMultiFileAuthState`. The session files are stored in the `./session` directory. On restart, the bot loads the existing session without requiring a new QR scan.

**Q: What happens if the AI API fails?**
A: The bot sends a fallback message: "I couldn't answer that right now. Type HELP or contact admin." All failures are logged to the `ai_calls` table with `success = 0`.

**Q: How do I deploy the bot to a VPS?**
A: 1) Clone the repo, 2) Run `npm install`, 3) Copy `.env.example` to `.env` and fill in secrets, 4) Run `node scripts/setup.js` to initialize the database, 5) Start with `pm2 start ecosystem.config.js`.

**Q: What is the admin panel URL?**
A: The admin panel runs on port 3000 (Next.js). In production, it's proxied through Nginx at https://bot.datacube.au.

**Q: How do I update the bot's context/knowledge base?**
A: Edit the markdown files in the `context/` directory. The bot caches context files in memory — restart the bot or call the cache invalidation endpoint to reload.

## Security

**Q: Is my WhatsApp data safe?**
A: The bot only stores a 100-character preview of messages (not full content). No personal data beyond your WhatsApp JID and display name is stored. Session files are stored locally and never transmitted.

**Q: How is the admin API secured?**
A: The Express API requires a Bearer token (`ADMIN_TOKEN`) in the Authorization header. CORS is restricted to the admin panel origin only.

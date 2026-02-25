# Datacube AU — Tech Stack Overview

## Frontend Stack
- **Next.js 14** with App Router (not Pages Router)
- **TypeScript** for type safety
- **Tailwind CSS** for styling
- **shadcn/ui** for component library
- **React Query (TanStack Query)** for server state
- **Zustand** for client state
- **NextAuth.js** for authentication

## Backend Stack
- **Node.js 20 LTS** runtime
- **Express.js** for REST API
- **better-sqlite3** for local SQLite
- **Supabase** for cloud PostgreSQL + Auth + Storage
- **Qdrant** for vector database (RAG)
- **Winston** for structured logging
- **PM2** for process management

## AI Stack
- **OpenRouter** as AI gateway (single API key, multiple models)
- **anthropic/claude-3-haiku** — default model (fast, cheap)
- **anthropic/claude-3.5-sonnet** — complex reasoning
- **openai/gpt-4o-mini** — RAG queries
- **OpenAI embeddings** — text-embedding-3-small for vectors

## WhatsApp Integration
- **@whiskeysockets/baileys** — WhatsApp Web MD protocol
- Multi-device support (no phone needed after scan)
- QR code login (shown on admin panel)
- Session persistence to disk

## Infrastructure
- **Ubuntu 22.04 LTS** VPS
- **Nginx** reverse proxy
- **Let's Encrypt** SSL certificates
- **GitHub Actions** CI/CD
- **PM2** process manager with cluster mode

## Development Tools
- **ESLint** + **Prettier** for code quality
- **Jest** for testing
- **dotenv** for environment variables
- **nodemon** for development hot-reload

## Key Packages
```
@whiskeysockets/baileys  — WhatsApp client
better-sqlite3           — SQLite database
express                  — REST API
axios                    — HTTP client
winston                  — Logging
dotenv                   — Environment config
qrcode                   — QR code generation
cors                     — CORS middleware
next                     — Admin panel framework
tailwindcss              — Styling
```

## Environment Variables
All secrets stored in `.env` file:
- `OPENROUTER_API_KEY` — AI API key
- `API_SECRET_KEY` — Express API auth
- `ADMIN_TOKEN` — Admin Bearer token
- `WA_SESSION_PATH` — WhatsApp session directory
- `DB_PATH` — SQLite database path

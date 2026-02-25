# Datacube AU — System Architecture

## Overview
Datacube AU is a developer platform and community focused on modern web architecture, AI integration, and cloud-native development. The platform provides tools, documentation, and community support for developers building production-grade applications.

## Core Stack

### Frontend
- **Framework**: Next.js 14 (App Router)
- **Styling**: Tailwind CSS
- **Language**: TypeScript
- **State Management**: React Query / Zustand
- **Auth**: NextAuth.js / Supabase Auth

### Backend
- **Runtime**: Node.js 20 LTS
- **API Framework**: Express.js / Fastify
- **Language**: JavaScript / TypeScript
- **Process Manager**: PM2
- **Authentication**: JWT tokens, Bearer auth

### Database Layer
- **Primary DB**: Supabase (PostgreSQL)
- **Vector DB**: Qdrant (for RAG/embeddings)
- **Cache**: Redis (optional)
- **Local/Bot**: SQLite (better-sqlite3)

### AI / ML
- **AI Gateway**: OpenRouter (model-agnostic)
- **Default Model**: anthropic/claude-3-haiku
- **Embeddings**: OpenAI text-embedding-3-small
- **RAG Pipeline**: Qdrant + custom retriever
- **Context Window**: 128k tokens (Claude 3)

### Infrastructure
- **Hosting**: VPS (Ubuntu 22.04 LTS)
- **Reverse Proxy**: Nginx
- **SSL**: Let's Encrypt (Certbot)
- **CI/CD**: GitHub Actions
- **Monitoring**: PM2 + custom health checks

### WhatsApp Bot
- **Library**: @whiskeysockets/baileys (multi-device)
- **Session**: Multi-file auth state (disk persistence)
- **Protocol**: WhatsApp Web MD (multi-device)
- **Login**: QR code (shown on admin panel)

## Key Design Decisions

### Why Baileys over whatsapp-web.js
- No Chromium dependency (lighter on VPS RAM)
- Multi-device support (MD protocol)
- Active maintenance
- Better for headless VPS environments

### Why SQLite for Bot
- Zero config, no separate DB server
- Sufficient for single VPS deployment
- WAL mode for concurrent reads
- Easy backup (single file)

### Why OpenRouter
- Single API key for multiple models
- Easy model switching without code changes
- Cost tracking per model
- Fallback model support

## API Design
- RESTful JSON API
- Bearer token authentication (ADMIN_TOKEN)
- Rate limiting per endpoint
- CORS restricted to admin panel origin
- All secrets in .env, never in code

## Security Model
- DM-only bot (no group processing)
- Opt-in required for AI replies
- No full message content stored (100-char preview only)
- Session files stored locally, never transmitted
- API protected by ADMIN_TOKEN Bearer auth

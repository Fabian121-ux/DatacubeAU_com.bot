const API_BASE = '/api/proxy';

type ApiFetchOptions = RequestInit & { skipContentType?: boolean };

async function apiFetch<T>(path: string, options: ApiFetchOptions = {}): Promise<T> {
  const { skipContentType, ...requestOptions } = options;
  const headers = new Headers(requestOptions.headers || {});

  if (!skipContentType && !headers.has('Content-Type') && requestOptions.body) {
    headers.set('Content-Type', 'application/json');
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...requestOptions,
    headers,
    credentials: 'same-origin',
    cache: 'no-store'
  });

  if (!response.ok) {
    const err = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(err.error || `API error: ${response.status}`);
  }

  return response.json();
}

export interface BotStatus {
  numberId?: number | null;
  ready: boolean;
  hasQR: boolean;
  state: 'booting' | 'waiting_qr' | 'connected' | 'disconnected' | string;
  lastSeen: string | null;
  lastConnectedAt: string | null;
  lastDisconnectReason: string | null;
  lastError: string | null;
  heartbeatAt: string | null;
  authState: string;
  hasSession: boolean;
  pairingCodeAvailable?: boolean;
  pairingCodeFor?: string | null;
  pairingCodeAt?: string | null;
  reconnectAttempts: number;
  uptime: number;
}

export interface BotNumber {
  id: number;
  phone: string;
  label: string | null;
  status: 'idle' | 'pairing' | 'connected' | 'disconnected' | string;
  last_connected_at: number | null;
  created_at: number;
}

export interface PairActionResponse {
  message: string;
  state: BotStatus;
}

export interface PairingCodeResponse {
  message: string;
  phoneNumber: string;
  pairingCode: string;
  createdAt: string;
  state: BotStatus;
}

export interface LegacyStatus {
  status: 'online' | 'connecting' | 'offline';
  isConnected: boolean;
  isConnecting: boolean;
  qrAvailable: boolean;
  uptime: number;
  reconnectAttempts: number;
  stats: {
    totalUsers: number;
    totalMessages: number;
    todayAiCalls: number;
    todayAiCost: number;
  };
  timestamp: string;
}

export interface User {
  id: number;
  jid: string;
  name: string | null;
  opted_in: number;
  first_seen: string;
  last_seen: string;
  message_count: number;
  ai_call_count: number;
}

export interface Message {
  id: number;
  jid: string;
  direction: 'in' | 'out';
  content_preview: string;
  handler: string;
  timestamp: string;
}

export interface AiCall {
  id: number;
  jid: string;
  model: string;
  prompt_tokens: number;
  completion_tokens: number;
  cost_usd: number;
  success: number;
  timestamp: string;
}

export interface ConfigEntry {
  value: string;
  updated_at: string;
}

export interface BroadcastResult {
  dryRun?: boolean;
  wouldSendTo?: number;
  users?: Array<{ jid: string; name: string | null }>;
  sent?: number;
  failed?: number;
  total?: number;
  message?: string;
}

export interface TrendsResponse {
  rangeDays: number;
  trends: {
    totals: {
      total_messages: number;
      ai_calls: number;
      cache_hits: number;
      ai_cost_usd: number;
    };
    topTopics: Array<{ topic: string; count: number }>;
    topCommands: Array<{ topic: string; count: number }>;
    daily: Array<{
      day: string;
      total_messages: number;
      ai_calls: number;
      cache_hits: number;
      ai_cost_usd: number;
    }>;
    cacheHitRate: number;
  };
  cache: {
    total_entries: number;
    total_hits: number;
    avg_hits: number;
  };
  ai: {
    total_calls: number;
    total_prompt_tokens: number;
    total_completion_tokens: number;
    total_cost_usd: number;
    successful_calls: number;
    failed_calls: number;
  };
  queue?: {
    queued: number;
    retrying: number;
    sending: number;
    sent: number;
    dead_letter: number;
  };
  kb?: {
    total_documents: number;
    active_documents: number;
    total_chunks: number;
  };
}

export interface CommandEntry {
  id: number;
  name: string;
  description: string;
  response_text: string;
  use_ai: number;
  tags: string;
  enabled: number;
  created_at: string;
  updated_at: string;
}

export interface KbDocument {
  id: number;
  title: string;
  source_type: string;
  fingerprint: string;
  tags: string;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface KbChunk {
  id: number;
  document_id: number;
  chunk_index: number;
  chunk_text: string;
  fingerprint: string;
  keywords: string;
  created_at: string;
}

export const api = {
  getLegacyStatus: () => apiFetch<LegacyStatus>('/status'),
  getBotStatus: () => apiFetch<BotStatus>('/bot/status'),
  getBotQrJson: () => apiFetch<{ state: string; qr: string | null; ready: boolean; hasQR: boolean }>('/bot/qr?format=json'),
  getBotQrImageUrl: () => `${API_BASE}/bot/qr`,
  reconnectBot: () => apiFetch<{ message: string }>('/bot/reconnect', { method: 'POST' }),
  getNumberStatus: (numberId: number) => apiFetch<BotStatus>(`/bot/status/${numberId}`),
  getNumberQrImageUrl: (numberId: number) => `${API_BASE}/bot/qr/${numberId}`,
  pairNumber: (numberId: number) => apiFetch<PairActionResponse>(`/bot/pair/${numberId}`, { method: 'POST' }),
  disconnectNumber: (numberId: number) =>
    apiFetch<PairActionResponse>(`/bot/disconnect/${numberId}`, { method: 'POST' }),
  getNumbers: () => apiFetch<{ numbers: BotNumber[]; count: number }>('/admin/numbers'),
  createNumber: (payload: { phone: string; label?: string }) =>
    apiFetch<{ number: BotNumber }>('/admin/numbers', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  updateNumber: (id: number, payload: Partial<{ phone: string; label: string; status: string }>) =>
    apiFetch<{ number: BotNumber }>(`/admin/numbers/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
  deleteNumber: (id: number) =>
    apiFetch<{ deleted: boolean; id: number }>(`/admin/numbers/${id}`, {
      method: 'DELETE'
    }),
  requestPairingCode: (phoneNumber: string, countryCode?: string) =>
    apiFetch<PairingCodeResponse>('/bot/pairing-code', {
      method: 'POST',
      body: JSON.stringify({ phoneNumber, countryCode })
    }),

  getUsers: (limit = 50, offset = 0) =>
    apiFetch<{ users: User[]; pagination: { total: number; limit: number; offset: number; hasMore: boolean }; summary?: { optedIn: number } }>(
      `/admin/users?limit=${limit}&offset=${offset}`
    ),
  getOptedInUsers: () => apiFetch<{ users: User[]; count: number }>('/users/opted-in'),

  getLogs: (limit = 50, offset = 0, jid?: string) =>
    apiFetch<{ messages: Message[]; count: number; limit: number; offset: number }>(
      `/logs?limit=${limit}&offset=${offset}${jid ? `&jid=${encodeURIComponent(jid)}` : ''}`
    ),
  getAiLogs: (limit = 50, offset = 0, jid?: string) =>
    apiFetch<{ calls: AiCall[]; stats: Record<string, number>; count: number; limit: number; offset: number }>(
      `/logs/ai?limit=${limit}&offset=${offset}${jid ? `&jid=${encodeURIComponent(jid)}` : ''}`
    ),
  getAdminLogs: (limit = 50, offset = 0) =>
    apiFetch<{
      messages: Message[];
      aiCalls: AiCall[];
      events: Array<{ id: number; category: string; topic: string; was_ai_used: number; cache_hit: number; ai_cost_usd: number; timestamp: string }>;
      queue?: { queued: number; retrying: number; sending: number; sent: number; dead_letter: number };
      count: { messages: number; aiCalls: number; events: number };
    }>(`/admin/logs?limit=${limit}&offset=${offset}`),

  getConfig: () => apiFetch<{ config: Record<string, ConfigEntry> }>('/admin/config'),
  updateConfig: (updates: Record<string, string>) =>
    apiFetch<{ updated: string[]; rejected: string[]; message: string }>('/admin/config', {
      method: 'PUT',
      body: JSON.stringify({ updates })
    }),
  invalidateContext: () => apiFetch<{ message: string }>('/admin/config/invalidate-context', { method: 'POST' }),

  getTrends: (days = 7) => apiFetch<TrendsResponse>(`/admin/trends?days=${days}`),

  getCommands: (includeDisabled = true) =>
    apiFetch<{ commands: CommandEntry[]; count: number }>(
      `/admin/commands?includeDisabled=${includeDisabled ? 'true' : 'false'}`
    ),
  createCommand: (payload: {
    name: string;
    description: string;
    response_text: string;
    use_ai: boolean;
    tags: string;
    enabled: boolean;
  }) =>
    apiFetch<{ command: CommandEntry }>('/admin/commands', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  updateCommand: (
    id: number,
    payload: Partial<{
      name: string;
      description: string;
      response_text: string;
      use_ai: boolean;
      tags: string;
      enabled: boolean;
    }>
  ) =>
    apiFetch<{ command: CommandEntry }>(`/admin/commands/${id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    }),
  deleteCommand: (id: number) =>
    apiFetch<{ deleted: boolean; id: number }>(`/admin/commands/${id}`, { method: 'DELETE' }),

  getTrainingDocuments: (limit = 50, offset = 0) =>
    apiFetch<{
      documents: KbDocument[];
      stats: { total_documents: number; active_documents: number; total_chunks: number };
      limits: { maxDocumentBytes: number };
    }>(`/admin/training/documents?limit=${limit}&offset=${offset}`),
  createTrainingDocument: (payload: {
    title: string;
    source_type: 'conversation' | 'site' | 'architecture' | 'general' | string;
    content: string;
    tags: string;
  }) =>
    apiFetch<{ document: KbDocument; chunkCount: number }>('/admin/training/documents', {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  getTrainingChunks: (documentId: number, limit = 200, offset = 0) =>
    apiFetch<{ chunks: KbChunk[]; count: number }>(
      `/admin/training/documents/${documentId}/chunks?limit=${limit}&offset=${offset}`
    ),
  deleteTrainingDocument: (id: number) =>
    apiFetch<{ deleted: boolean; id: number }>(`/admin/training/documents/${id}`, {
      method: 'DELETE'
    }),

  broadcast: (message: string, dryRun = false) =>
    apiFetch<BroadcastResult>('/broadcast', {
      method: 'POST',
      body: JSON.stringify({ message, dryRun })
    }),
  restart: () => apiFetch<{ message: string }>('/restart', { method: 'POST' })
};

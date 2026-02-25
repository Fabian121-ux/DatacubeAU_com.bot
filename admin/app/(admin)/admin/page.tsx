'use client';

import { useEffect, useMemo, useState } from 'react';
import Link from 'next/link';
import { RefreshCw, Wifi, QrCode, CheckCircle2, RotateCcw, AlertTriangle } from 'lucide-react';
import { api, type BotStatus, type LegacyStatus } from '@/lib/api-client';

function formatUptime(seconds: number): string {
  if (!seconds) return '0m';
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m`;
  return `${Math.floor(minutes / 60)}h ${minutes % 60}m`;
}

export default function DashboardPage() {
  const [botStatus, setBotStatus] = useState<BotStatus | null>(null);
  const [legacyStatus, setLegacyStatus] = useState<LegacyStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadStatus(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const [bot, legacy] = await Promise.all([api.getBotStatus(), api.getLegacyStatus()]);
      setBotStatus(bot);
      setLegacyStatus(legacy);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load status.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadStatus();
    const timer = setInterval(() => loadStatus(), 1500);
    return () => clearInterval(timer);
  }, []);

  const statusLabel = useMemo(() => {
    if (!botStatus) return 'unknown';
    return botStatus.state || botStatus.authState;
  }, [botStatus]);

  const qrImageUrl = `${api.getBotQrImageUrl()}?ts=${Date.now()}`;

  async function reconnectBot() {
    setReconnecting(true);
    try {
      await api.reconnectBot();
      await loadStatus(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to reconnect bot.');
    } finally {
      setReconnecting(false);
    }
  }

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Admin Dashboard</h1>
            <p className="mt-2 text-sm text-slate-400">Live bot status, QR state, and usage metrics.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadStatus(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
            >
              <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
            <button
              type="button"
              onClick={reconnectBot}
              disabled={reconnecting}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(245,176,104,0.55)] hover:text-white disabled:opacity-65"
            >
              <RotateCcw size={13} className={reconnecting ? 'animate-spin' : ''} />
              Reconnect
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Auth State</p>
            <p className="mt-2 text-lg font-semibold text-white">{botStatus?.state || statusLabel}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Uptime</p>
            <p className="mt-2 text-lg font-semibold text-white">{formatUptime(legacyStatus?.uptime || 0)}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Users</p>
            <p className="mt-2 text-lg font-semibold text-white">{legacyStatus?.stats.totalUsers ?? '-'}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.16em] text-slate-500">AI Calls Today</p>
            <p className="mt-2 text-lg font-semibold text-white">{legacyStatus?.stats.todayAiCalls ?? '-'}</p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-2 text-xs text-slate-400">
          <Wifi size={12} />
          {legacyStatus?.timestamp ? `Updated ${new Date(legacyStatus.timestamp).toLocaleString()}` : 'Waiting for API'}
        </div>

        {(botStatus?.state === 'failed' || botStatus?.lastError) && (
          <p className="mt-4 flex items-center gap-2 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            <AlertTriangle size={15} />
            {botStatus?.lastError || 'Bot is disconnected.'}
          </p>
        )}

        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      <section className="grid gap-4 lg:grid-cols-[1fr_auto]">
        <div className="panel p-4">
          <h2 className="text-lg font-semibold text-white">Connection State</h2>
          {botStatus?.ready ? (
            <div className="mt-4 flex items-center gap-2 text-emerald-200">
              <CheckCircle2 size={18} />
              Connected
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              <p className="text-sm text-slate-300">
                Not connected yet. Current state: <strong>{botStatus?.state || 'unknown'}</strong>
              </p>
              <p className="text-sm text-slate-400">QR auto-refresh is active every 1.5 seconds.</p>
            </div>
          )}

          {botStatus?.ready && (
            <div className="mt-4 grid gap-2 text-xs text-slate-300 sm:grid-cols-2">
              <div className="panel-soft px-3 py-2">
                <p className="text-slate-500">Session Stored</p>
                <p className="mt-1 text-slate-100">{botStatus.hasSession ? 'yes' : 'no'}</p>
              </div>
              <div className="panel-soft px-3 py-2">
                <p className="text-slate-500">Last Connected</p>
                <p className="mt-1 text-slate-100">
                  {botStatus.lastConnectedAt ? new Date(botStatus.lastConnectedAt).toLocaleString() : '-'}
                </p>
              </div>
            </div>
          )}

          <div className="mt-5 flex flex-wrap gap-2">
            <Link href="/admin/qr" className="rounded-lg border border-[rgba(255,255,255,0.2)] px-3 py-2 text-sm text-slate-200 hover:text-white">
              Open Full QR View
            </Link>
            <Link href="/admin/settings" className="rounded-lg border border-[rgba(255,255,255,0.2)] px-3 py-2 text-sm text-slate-200 hover:text-white">
              Settings
            </Link>
            <Link href="/admin/trends" className="rounded-lg border border-[rgba(255,255,255,0.2)] px-3 py-2 text-sm text-slate-200 hover:text-white">
              Trends
            </Link>
          </div>
        </div>

        <div className="panel flex min-h-[280px] min-w-[280px] items-center justify-center p-4">
          {loading ? (
            <p className="text-sm text-slate-400">Loading...</p>
          ) : botStatus?.ready ? (
            <div className="text-center text-emerald-200">
              <CheckCircle2 size={32} className="mx-auto mb-2" />
              <p>Connected</p>
            </div>
          ) : botStatus?.hasQR ? (
            <div className="rounded-xl bg-white p-3">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={qrImageUrl} alt="QR Code" className="h-64 w-64 rounded-md object-contain" />
            </div>
          ) : (
            <div className="text-center text-slate-400">
              <QrCode size={28} className="mx-auto mb-2 opacity-60" />
              <p>No QR yet ({botStatus?.state || botStatus?.authState || 'waiting'})</p>
            </div>
          )}
        </div>
      </section>
    </div>
  );
}

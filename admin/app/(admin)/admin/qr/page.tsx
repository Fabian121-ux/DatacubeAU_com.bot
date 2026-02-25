'use client';

import { useEffect, useMemo, useState } from 'react';
import { RefreshCw, QrCode, CheckCircle2, RotateCcw, AlertTriangle } from 'lucide-react';
import { api, type BotStatus } from '@/lib/api-client';

export default function QRPage() {
  const [status, setStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [reconnecting, setReconnecting] = useState(false);
  const [pairingLoading, setPairingLoading] = useState(false);
  const [pairingPhone, setPairingPhone] = useState('');
  const [countryCode, setCountryCode] = useState('');
  const [pairingCode, setPairingCode] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  async function loadStatus(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const next = await api.getBotStatus();
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load QR status.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadStatus();
    const timer = setInterval(() => {
      setTick((v) => v + 1);
      loadStatus();
    }, 1500);
    return () => clearInterval(timer);
  }, []);

  const qrUrl = useMemo(() => `${api.getBotQrImageUrl()}?ts=${Date.now()}-${tick}`, [tick]);

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

  async function requestPairingCode() {
    if (!pairingPhone.trim()) {
      setError('Enter a phone number first.');
      return;
    }

    setPairingLoading(true);
    try {
      const response = await api.requestPairingCode(pairingPhone, countryCode || undefined);
      setPairingCode(response.pairingCode);
      setError(null);
      await loadStatus(true);
    } catch (err) {
      setPairingCode(null);
      setError(err instanceof Error ? err.message : 'Failed to generate pairing code.');
    } finally {
      setPairingLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">QR Login</h1>
            <p className="mt-2 text-sm text-slate-400">Polling every 1.5 seconds until connection is ready.</p>
          </div>
          <div className="flex gap-2">
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

        <div className="mt-4 rounded-xl border border-[rgba(255,255,255,0.1)] bg-[rgba(8,20,34,0.75)] p-3 text-sm text-slate-300">
          state: <strong>{status?.state || status?.authState || 'loading'}</strong>
        </div>

        {(status?.state === 'failed' || status?.lastError) && (
          <p className="mt-4 flex items-center gap-2 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            <AlertTriangle size={15} />
            {status?.lastError || 'Bot disconnected'}
          </p>
        )}

        <div className="mt-4 space-y-3 rounded-xl border border-[rgba(255,255,255,0.1)] bg-[rgba(8,20,34,0.75)] p-3">
          <p className="text-xs uppercase tracking-wide text-slate-400">Pair by phone number</p>
          <div className="grid gap-2 md:grid-cols-[120px_1fr_auto]">
            <input
              type="text"
              value={countryCode}
              onChange={(event) => setCountryCode(event.target.value)}
              placeholder="Country code"
              className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-[rgba(32,197,165,0.55)]"
            />
            <input
              type="text"
              value={pairingPhone}
              onChange={(event) => setPairingPhone(event.target.value)}
              placeholder="Phone number"
              className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-[rgba(32,197,165,0.55)]"
            />
            <button
              type="button"
              onClick={requestPairingCode}
              disabled={pairingLoading}
              className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
            >
              {pairingLoading ? 'Generating...' : 'Get code'}
            </button>
          </div>
          {pairingCode && (
            <div className="rounded-lg border border-emerald-400/35 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
              Pairing code: <strong className="tracking-widest">{pairingCode}</strong>
            </div>
          )}
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      <section className="panel flex min-h-[360px] items-center justify-center p-5">
        {loading ? (
          <p className="text-sm text-slate-400">Loading...</p>
        ) : status?.ready ? (
          <div className="text-center text-emerald-200">
            <CheckCircle2 size={36} className="mx-auto mb-2" />
            <p className="text-lg font-semibold">Connected</p>
          </div>
        ) : status?.hasQR ? (
          <div className="rounded-xl bg-white p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrUrl} alt="WhatsApp QR Code" className="h-72 w-72 rounded-md object-contain" />
          </div>
        ) : (
          <div className="text-center text-slate-400">
            <QrCode size={32} className="mx-auto mb-2 opacity-60" />
            <p>No QR available yet. Current state: {status?.state || status?.authState || 'unknown'}</p>
          </div>
        )}
      </section>
    </div>
  );
}

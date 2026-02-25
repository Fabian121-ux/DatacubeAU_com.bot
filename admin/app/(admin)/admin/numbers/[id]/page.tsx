'use client';

import Link from 'next/link';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'next/navigation';
import { ArrowLeft, RefreshCw, CheckCircle2, QrCode, RotateCcw, Power, AlertTriangle } from 'lucide-react';
import { api, type BotStatus } from '@/lib/api-client';

function normalizeId(raw: string | string[] | undefined): number | null {
  if (!raw) return null;
  const value = Array.isArray(raw) ? raw[0] : raw;
  const id = Number(value);
  return Number.isFinite(id) && id > 0 ? id : null;
}

function formatDate(value: string | null): string {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

export default function NumberDetailPage() {
  const params = useParams<{ id: string }>();
  const numberId = normalizeId(params?.id);

  const [status, setStatus] = useState<BotStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [acting, setActing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tick, setTick] = useState(0);

  const loadStatus = useCallback(async (manual = false) => {
    if (!numberId) return;
    if (manual) setRefreshing(true);
    try {
      const next = await api.getNumberStatus(numberId);
      setStatus(next);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load number status.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [numberId]);

  useEffect(() => {
    if (!numberId) return;
    loadStatus();
    const timer = setInterval(() => {
      setTick((v) => v + 1);
      loadStatus();
    }, 1500);
    return () => clearInterval(timer);
  }, [numberId, loadStatus]);

  const qrUrl = useMemo(() => {
    if (!numberId) return '';
    return `${api.getNumberQrImageUrl(numberId)}?ts=${Date.now()}-${tick}`;
  }, [numberId, tick]);

  async function pairNow() {
    if (!numberId) return;
    setActing(true);
    try {
      await api.pairNumber(numberId);
      await loadStatus(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start pairing.');
    } finally {
      setActing(false);
    }
  }

  async function disconnectNow() {
    if (!numberId) return;
    setActing(true);
    try {
      await api.disconnectNumber(numberId);
      await loadStatus(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to disconnect.');
    } finally {
      setActing(false);
    }
  }

  if (!numberId) {
    return (
      <div className="panel p-5 text-sm text-red-200">
        Invalid number id.
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-3xl space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <Link href="/admin/numbers" className="inline-flex items-center gap-1 text-xs text-slate-400 hover:text-slate-200">
              <ArrowLeft size={13} />
              Back to Numbers
            </Link>
            <h1 className="section-title mt-2">Number #{numberId}</h1>
            <p className="mt-2 text-sm text-slate-400">Live pairing state and QR lifecycle.</p>
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
              onClick={pairNow}
              disabled={acting}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(245,176,104,0.55)] hover:text-white disabled:opacity-65"
            >
              <RotateCcw size={13} className={acting ? 'animate-spin' : ''} />
              Reconnect
            </button>
            <button
              type="button"
              onClick={disconnectNow}
              disabled={acting}
              className="inline-flex items-center gap-2 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-xs font-medium text-red-200 transition hover:bg-red-500/20 disabled:opacity-65"
            >
              <Power size={13} />
              Disconnect
            </button>
          </div>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">State</p>
            <p className="mt-2 text-base font-semibold text-white">{status?.state || 'loading'}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.14em] text-slate-500">Last Connected</p>
            <p className="mt-2 text-sm text-slate-200">{formatDate(status?.lastConnectedAt || null)}</p>
          </div>
        </div>

        {(status?.state === 'disconnected' || status?.lastError) && (
          <p className="mt-4 flex items-center gap-2 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            <AlertTriangle size={15} />
            {status?.lastError || 'Disconnected'}
          </p>
        )}

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
        ) : status?.state === 'waiting_qr' && status?.hasQR ? (
          <div className="rounded-xl bg-white p-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={qrUrl} alt="WhatsApp QR Code" className="h-72 w-72 rounded-md object-contain" />
          </div>
        ) : (
          <div className="text-center text-slate-400">
            <QrCode size={32} className="mx-auto mb-2 opacity-60" />
            <p>No QR available yet. Current state: {status?.state || 'unknown'}</p>
          </div>
        )}
      </section>
    </div>
  );
}

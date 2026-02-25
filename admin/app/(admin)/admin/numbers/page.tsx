'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { Plus, RefreshCw, Power, PlugZap, Trash2, ExternalLink } from 'lucide-react';
import { api, type BotNumber } from '@/lib/api-client';

function formatTs(ts: number | null): string {
  if (!ts) return '-';
  return new Date(ts).toLocaleString();
}

function statusClass(status: string): string {
  if (status === 'connected') return 'border-emerald-400/30 bg-emerald-500/12 text-emerald-200';
  if (status === 'pairing') return 'border-amber-400/30 bg-amber-500/12 text-amber-200';
  if (status === 'idle') return 'border-sky-400/30 bg-sky-500/12 text-sky-200';
  return 'border-slate-400/20 bg-slate-500/10 text-slate-300';
}

function normalizePhoneInput(value: string): string {
  return value.replace(/\D/g, '');
}

export default function NumbersPage() {
  const [numbers, setNumbers] = useState<BotNumber[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [actingId, setActingId] = useState<number | null>(null);
  const [phone, setPhone] = useState('');
  const [label, setLabel] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadNumbers(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const response = await api.getNumbers();
      setNumbers(response.numbers || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load numbers.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadNumbers();
  }, []);

  const connectedCount = useMemo(
    () => numbers.filter((item) => item.status === 'connected').length,
    [numbers]
  );

  async function addNumber(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!phone.trim()) {
      setError('Phone is required');
      return;
    }

    setSubmitting(true);
    setError(null);
    setNotice(null);
    try {
      await api.createNumber({
        phone: normalizePhoneInput(phone),
        label: label.trim()
      });
      setPhone('');
      setLabel('');
      setNotice('Number added.');
      await loadNumbers();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to add number.');
    } finally {
      setSubmitting(false);
    }
  }

  async function runAction(id: number, action: 'pair' | 'disconnect' | 'remove') {
    setActingId(id);
    setError(null);
    setNotice(null);
    try {
      if (action === 'pair') {
        await api.pairNumber(id);
        setNotice(`Pairing started for number #${id}.`);
      } else if (action === 'disconnect') {
        await api.disconnectNumber(id);
        setNotice(`Number #${id} disconnected.`);
      } else {
        const confirmed = window.confirm('Remove this number and delete its session?');
        if (!confirmed) return;
        await api.deleteNumber(id);
        setNotice(`Number #${id} removed.`);
      }
      await loadNumbers();
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} number.`);
    } finally {
      setActingId(null);
    }
  }

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Numbers</h1>
            <p className="mt-2 text-sm text-slate-400">
              Manage WhatsApp numbers, pairing state, and active sessions.
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadNumbers(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Total Numbers</p>
            <p className="mt-2 text-2xl font-semibold text-white">{numbers.length}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Connected</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-200">{connectedCount}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Pairing</p>
            <p className="mt-2 text-2xl font-semibold text-amber-200">
              {numbers.filter((item) => item.status === 'pairing').length}
            </p>
          </div>
        </div>

        <form onSubmit={addNumber} className="mt-4 grid gap-2 md:grid-cols-[1fr_1fr_auto]">
          <input
            value={phone}
            onChange={(event) => setPhone(normalizePhoneInput(event.target.value))}
            placeholder="Phone (E.164 digits, e.g. 2349...)"
            className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-[rgba(32,197,165,0.55)]"
          />
          <input
            value={label}
            onChange={(event) => setLabel(event.target.value)}
            placeholder="Label (optional)"
            className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-sm text-slate-100 outline-none ring-0 placeholder:text-slate-500 focus:border-[rgba(32,197,165,0.55)]"
          />
          <button
            type="submit"
            disabled={submitting}
            className="inline-flex items-center justify-center gap-2 rounded-lg bg-gradient-to-r from-[var(--brand-1)] to-[var(--brand-2)] px-4 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
          >
            <Plus size={14} />
            {submitting ? 'Adding...' : 'Add Number'}
          </button>
        </form>

        {notice && (
          <p className="mt-4 rounded-lg border border-emerald-400/35 bg-emerald-500/10 px-3 py-2 text-sm text-emerald-100">
            {notice}
          </p>
        )}

        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      <section className="panel p-0">
        {loading ? (
          <div className="p-5 text-sm text-slate-400">Loading numbers...</div>
        ) : numbers.length === 0 ? (
          <div className="p-5 text-sm text-slate-400">No numbers configured yet.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[900px] text-left text-sm">
              <thead className="border-b border-[rgba(255,255,255,0.08)] text-xs uppercase tracking-[0.14em] text-slate-500">
                <tr>
                  <th className="px-4 py-3 font-medium">Phone</th>
                  <th className="px-4 py-3 font-medium">Label</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium">Last Connected</th>
                  <th className="px-4 py-3 font-medium text-right">Actions</th>
                </tr>
              </thead>
              <tbody>
                {numbers.map((item) => (
                  <tr key={item.id} className="border-b border-[rgba(255,255,255,0.06)] last:border-0">
                    <td className="mono px-4 py-3 text-[13px] text-slate-200">{item.phone}</td>
                    <td className="px-4 py-3 text-white">{item.label || '-'}</td>
                    <td className="px-4 py-3">
                      <span className={`badge ${statusClass(item.status)}`}>{item.status}</span>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{formatTs(item.last_connected_at)}</td>
                    <td className="px-4 py-3 text-right">
                      <div className="inline-flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => runAction(item.id, 'pair')}
                          disabled={actingId === item.id}
                          className="inline-flex items-center gap-1 rounded-lg border border-amber-400/35 px-2 py-1 text-xs text-amber-200"
                        >
                          <PlugZap size={12} />
                          Pair
                        </button>
                        <button
                          type="button"
                          onClick={() => runAction(item.id, 'disconnect')}
                          disabled={actingId === item.id}
                          className="inline-flex items-center gap-1 rounded-lg border border-[rgba(255,255,255,0.2)] px-2 py-1 text-xs text-slate-200"
                        >
                          <Power size={12} />
                          Disconnect
                        </button>
                        <Link
                          href={`/admin/numbers/${item.id}`}
                          className="inline-flex items-center gap-1 rounded-lg border border-[rgba(255,255,255,0.2)] px-2 py-1 text-xs text-slate-200"
                        >
                          <ExternalLink size={12} />
                          Manage
                        </Link>
                        <button
                          type="button"
                          onClick={() => runAction(item.id, 'remove')}
                          disabled={actingId === item.id}
                          className="inline-flex items-center gap-1 rounded-lg border border-red-400/35 px-2 py-1 text-xs text-red-200"
                        >
                          <Trash2 size={12} />
                          Remove
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}

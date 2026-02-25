'use client';

import { useMemo, useState } from 'react';
import { Megaphone, Send, Search, AlertTriangle } from 'lucide-react';
import { api, type BroadcastResult } from '@/lib/api-client';

const MAX_BROADCAST_CHARS = 4000;

export default function BroadcastPage() {
  const [message, setMessage] = useState('');
  const [dryRun, setDryRun] = useState(true);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<BroadcastResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const remainingChars = useMemo(() => MAX_BROADCAST_CHARS - message.length, [message.length]);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!message.trim()) {
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const response = await api.broadcast(message.trim(), dryRun);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Broadcast failed.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex items-center gap-2">
          <Megaphone size={18} className="text-[var(--brand-2)]" />
          <h1 className="section-title">Broadcast Center</h1>
        </div>
        <p className="mt-2 text-sm text-slate-400">
          Send one announcement to all opted-in users with built-in dry-run mode.
        </p>
      </section>

      <section className="rounded-xl border border-amber-400/35 bg-amber-500/10 p-4 text-sm text-amber-100">
        <p className="flex items-center gap-2">
          <AlertTriangle size={15} />
          Broadcast sending is rate-limited to one execution every 24 hours.
        </p>
      </section>

      <section className="panel p-5">
        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm text-slate-300">Message Body</span>
            <textarea
              value={message}
              onChange={(event) => setMessage(event.target.value)}
              rows={8}
              maxLength={MAX_BROADCAST_CHARS}
              placeholder="Write your announcement..."
              className="w-full rounded-xl border border-[rgba(255,255,255,0.1)] bg-[rgba(9,23,38,0.85)] p-3 text-sm text-white outline-none transition focus:border-[rgba(32,197,165,0.6)]"
            />
            <p className="mt-2 text-xs text-slate-500">
              {message.length}/{MAX_BROADCAST_CHARS} characters ({remainingChars} remaining)
            </p>
          </label>

          <label className="panel-soft flex items-center justify-between px-3 py-2">
            <div>
              <p className="text-sm text-white">Dry Run</p>
              <p className="text-xs text-slate-400">Preview recipient count without sending messages.</p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={dryRun}
              onClick={() => setDryRun((value) => !value)}
              className={`relative h-7 w-12 rounded-full transition ${
                dryRun ? 'bg-[rgba(32,197,165,0.65)]' : 'bg-[rgba(255,255,255,0.2)]'
              }`}
            >
              <span
                className={`absolute top-1 h-5 w-5 rounded-full bg-white transition ${
                  dryRun ? 'left-6' : 'left-1'
                }`}
              />
            </button>
          </label>

          <button
            type="submit"
            disabled={loading || !message.trim()}
            className={`inline-flex items-center gap-2 rounded-xl px-4 py-2 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
              dryRun
                ? 'bg-gradient-to-r from-cyan-400 to-teal-400 text-slate-950 hover:brightness-105'
                : 'bg-gradient-to-r from-orange-400 to-red-400 text-slate-950 hover:brightness-105'
            }`}
          >
            {dryRun ? <Search size={15} /> : <Send size={15} />}
            {loading ? 'Processing...' : dryRun ? 'Preview Recipients' : 'Send Broadcast'}
          </button>
        </form>
      </section>

      {error && (
        <section className="rounded-xl border border-red-400/35 bg-red-500/10 p-4 text-sm text-red-200">
          {error}
        </section>
      )}

      {result && (
        <section className="panel-soft p-4 text-sm">
          {result.dryRun ? (
            <p className="text-cyan-100">
              Dry run complete: would send to <strong>{result.wouldSendTo ?? 0}</strong> opted-in users.
            </p>
          ) : (
            <p className="text-emerald-100">
              Broadcast complete: sent <strong>{result.sent ?? 0}</strong>, failed{' '}
              <strong>{result.failed ?? 0}</strong>, total <strong>{result.total ?? 0}</strong>.
            </p>
          )}
          {result.message ? <p className="mt-2 text-slate-300">{result.message}</p> : null}
        </section>
      )}
    </div>
  );
}

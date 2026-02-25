'use client';

import { useCallback, useEffect, useMemo, useState } from 'react';
import { RefreshCw } from 'lucide-react';
import { api, type TrendsResponse } from '@/lib/api-client';

export default function TrendsPage() {
  const [days, setDays] = useState(7);
  const [data, setData] = useState<TrendsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadTrends = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const response = await api.getTrends(days);
      setData(response);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load trends.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [days]);

  useEffect(() => {
    loadTrends();
  }, [loadTrends]);

  const cacheHitPercent = useMemo(() => {
    if (!data) return 0;
    return Math.round((data.trends.cacheHitRate || 0) * 100);
  }, [data]);

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Trends</h1>
            <p className="mt-2 text-sm text-slate-400">Top topics, cache effectiveness, and AI spend.</p>
          </div>
          <div className="flex items-center gap-2">
            <select
              value={days}
              onChange={(event) => setDays(Number(event.target.value))}
              className="rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-2 py-2 text-xs text-slate-200 outline-none"
            >
              <option value={7}>7 days</option>
              <option value={14}>14 days</option>
              <option value={30}>30 days</option>
            </select>
            <button
              type="button"
              onClick={() => loadTrends(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
            >
              <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
              Refresh
            </button>
          </div>
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      {loading || !data ? (
        <section className="panel p-5 text-sm text-slate-400">Loading trends...</section>
      ) : (
        <>
          <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            <div className="panel-soft p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Messages</p>
              <p className="mt-2 text-xl font-semibold text-white">{data.trends.totals.total_messages}</p>
            </div>
            <div className="panel-soft p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">AI Calls</p>
              <p className="mt-2 text-xl font-semibold text-white">{data.trends.totals.ai_calls}</p>
            </div>
            <div className="panel-soft p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Cache Hit Rate</p>
              <p className="mt-2 text-xl font-semibold text-white">{cacheHitPercent}%</p>
            </div>
            <div className="panel-soft p-3">
              <p className="text-xs uppercase tracking-[0.16em] text-slate-500">AI Spend</p>
              <p className="mt-2 text-xl font-semibold text-white">${Number(data.trends.totals.ai_cost_usd || 0).toFixed(4)}</p>
            </div>
          </section>

          {(data.queue || data.kb) && (
            <section className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <div className="panel-soft p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Queue Dead-Letter</p>
                <p className="mt-2 text-xl font-semibold text-white">{data.queue?.dead_letter ?? 0}</p>
              </div>
              <div className="panel-soft p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">Queue Pending</p>
                <p className="mt-2 text-xl font-semibold text-white">
                  {(data.queue?.queued ?? 0) + (data.queue?.retrying ?? 0)}
                </p>
              </div>
              <div className="panel-soft p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">KB Documents</p>
                <p className="mt-2 text-xl font-semibold text-white">{data.kb?.total_documents ?? 0}</p>
              </div>
              <div className="panel-soft p-3">
                <p className="text-xs uppercase tracking-[0.16em] text-slate-500">KB Chunks</p>
                <p className="mt-2 text-xl font-semibold text-white">{data.kb?.total_chunks ?? 0}</p>
              </div>
            </section>
          )}

          <section className="grid gap-4 lg:grid-cols-2">
            <div className="panel p-4">
              <h2 className="mb-3 text-base font-semibold text-white">Top Intents</h2>
              <div className="space-y-2 text-sm">
                {data.trends.topTopics.map((item) => (
                  <div key={item.topic} className="panel-soft flex items-center justify-between px-3 py-2">
                    <span className="text-slate-200">{item.topic}</span>
                    <span className="text-slate-400">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="panel p-4">
              <h2 className="mb-3 text-base font-semibold text-white">Top Commands</h2>
              <div className="space-y-2 text-sm">
                {data.trends.topCommands.map((item) => (
                  <div key={item.topic} className="panel-soft flex items-center justify-between px-3 py-2">
                    <span className="text-slate-200">{item.topic}</span>
                    <span className="text-slate-400">{item.count}</span>
                  </div>
                ))}
              </div>
            </div>
          </section>
        </>
      )}
    </div>
  );
}

'use client';

import { useEffect, useMemo, useState } from 'react';
import { Save, RefreshCw, ShieldAlert, RotateCw, Gauge } from 'lucide-react';
import { api, type ConfigEntry } from '@/lib/api-client';

type ConfigMap = Record<string, ConfigEntry>;

export default function ConfigPage() {
  const [config, setConfig] = useState<ConfigMap>({});
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [actionLoading, setActionLoading] = useState<'context' | 'restart' | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadConfig(manual = false) {
    if (manual) {
      setRefreshing(true);
    }

    try {
      const response = await api.getConfig();
      setConfig(response.config);
      setDrafts(
        Object.fromEntries(
          Object.entries(response.config).map(([key, entry]) => [key, entry.value])
        )
      );
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load config.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadConfig();
  }, []);

  const dirtyKeys = useMemo(() => {
    return Object.keys(drafts).filter((key) => drafts[key] !== config[key]?.value);
  }, [config, drafts]);

  async function saveChanges() {
    if (dirtyKeys.length === 0) {
      setNotice('No changes to save.');
      return;
    }

    setSaving(true);
    setNotice(null);
    setError(null);

    const updates = Object.fromEntries(dirtyKeys.map((key) => [key, drafts[key]]));

    try {
      const response = await api.updateConfig(updates);
      setNotice(response.message || `${response.updated.length} config values updated.`);
      await loadConfig();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save config changes.');
    } finally {
      setSaving(false);
    }
  }

  async function invalidateContext() {
    setActionLoading('context');
    setNotice(null);
    setError(null);
    try {
      const response = await api.invalidateContext();
      setNotice(response.message);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to invalidate context.');
    } finally {
      setActionLoading(null);
    }
  }

  async function restartBot() {
    const confirmed = window.confirm('Send restart signal to bot process now?');
    if (!confirmed) {
      return;
    }

    setActionLoading('restart');
    setNotice(null);
    setError(null);
    try {
      const response = await api.restart();
      setNotice(response.message || 'Restart signal sent.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to send restart signal.');
    } finally {
      setActionLoading(null);
    }
  }

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Runtime Configuration</h1>
            <p className="mt-2 text-sm text-slate-400">
              Update operational values instantly without redeploying the bot.
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => loadConfig(true)}
              disabled={refreshing}
              className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
            >
              <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
              Reload
            </button>
            <button
              type="button"
              onClick={saveChanges}
              disabled={saving || dirtyKeys.length === 0}
              className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-[var(--brand-1)] to-[var(--brand-2)] px-3 py-2 text-xs font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-65"
            >
              <Save size={13} />
              {saving ? 'Saving...' : `Save ${dirtyKeys.length || ''}`.trim()}
            </button>
          </div>
        </div>

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

      <section className="panel p-4 md:p-5">
        {loading ? (
          <p className="text-sm text-slate-400">Loading config values...</p>
        ) : (
          <div className="space-y-3">
            {Object.entries(config).map(([key, entry]) => {
              const isDirty = drafts[key] !== entry.value;
              return (
                <div key={key} className="panel-soft p-3">
                  <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
                    <p className="mono text-sm text-[var(--brand-1)]">{key}</p>
                    <span className="text-xs text-slate-500">
                      Updated {new Date(entry.updated_at).toLocaleString()}
                    </span>
                  </div>
                  <input
                    value={drafts[key] ?? ''}
                    onChange={(event) =>
                      setDrafts((prev) => ({ ...prev, [key]: event.target.value }))
                    }
                    className={`w-full rounded-lg border bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none transition ${
                      isDirty
                        ? 'border-[rgba(245,176,104,0.65)]'
                        : 'border-[rgba(255,255,255,0.1)]'
                    }`}
                  />
                </div>
              );
            })}
          </div>
        )}
      </section>

      <section className="grid gap-3 lg:grid-cols-2">
        <div className="panel-soft p-4">
          <div className="flex items-center gap-2">
            <Gauge size={15} className="text-[var(--brand-1)]" />
            <h2 className="text-base font-semibold text-white">Context Cache</h2>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Force a context reload if markdown knowledge files changed.
          </p>
          <button
            type="button"
            onClick={invalidateContext}
            disabled={actionLoading === 'context'}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(8,20,34,0.9)] px-3 py-2 text-sm text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-60"
          >
            <RefreshCw size={13} className={actionLoading === 'context' ? 'animate-spin' : ''} />
            Reload Context
          </button>
        </div>

        <div className="panel-soft p-4">
          <div className="flex items-center gap-2">
            <ShieldAlert size={15} className="text-[var(--brand-2)]" />
            <h2 className="text-base font-semibold text-white">Process Control</h2>
          </div>
          <p className="mt-2 text-sm text-slate-400">
            Send a graceful restart signal to PM2-managed bot process.
          </p>
          <button
            type="button"
            onClick={restartBot}
            disabled={actionLoading === 'restart'}
            className="mt-3 inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(8,20,34,0.9)] px-3 py-2 text-sm text-slate-200 transition hover:border-[rgba(245,176,104,0.55)] hover:text-white disabled:opacity-60"
          >
            <RotateCw size={13} className={actionLoading === 'restart' ? 'animate-spin' : ''} />
            Restart Bot
          </button>
        </div>
      </section>
    </div>
  );
}

'use client';

import { useEffect, useState } from 'react';
import { Plus, RefreshCw, Save, Trash2, Pencil, X } from 'lucide-react';
import { api, type CommandEntry } from '@/lib/api-client';

type Draft = {
  name: string;
  description: string;
  response_text: string;
  use_ai: boolean;
  tags: string;
  enabled: boolean;
};

const EMPTY_DRAFT: Draft = {
  name: '',
  description: '',
  response_text: '',
  use_ai: false,
  tags: '',
  enabled: true
};

export default function CommandsPage() {
  const [commands, setCommands] = useState<CommandEntry[]>([]);
  const [draft, setDraft] = useState<Draft>(EMPTY_DRAFT);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function loadCommands(manual = false) {
    if (manual) setRefreshing(true);
    try {
      const response = await api.getCommands(true);
      setCommands(response.commands || []);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load commands.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadCommands();
  }, []);

  function resetDraft() {
    setDraft(EMPTY_DRAFT);
    setEditingId(null);
  }

  function startEdit(command: CommandEntry) {
    setEditingId(command.id);
    setDraft({
      name: command.name,
      description: command.description || '',
      response_text: command.response_text,
      use_ai: Boolean(command.use_ai),
      tags: command.tags || '',
      enabled: Boolean(command.enabled)
    });
  }

  async function submitDraft(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError(null);
    setNotice(null);

    try {
      if (editingId) {
        await api.updateCommand(editingId, draft);
        setNotice('Command updated.');
      } else {
        await api.createCommand(draft);
        setNotice('Command created.');
      }
      resetDraft();
      await loadCommands();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save command.');
    } finally {
      setSaving(false);
    }
  }

  async function removeCommand(command: CommandEntry) {
    const confirmed = window.confirm(`Delete command "${command.name}"?`);
    if (!confirmed) return;
    setError(null);
    setNotice(null);
    try {
      await api.deleteCommand(command.id);
      setNotice('Command deleted.');
      if (editingId === command.id) {
        resetDraft();
      }
      await loadCommands();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete command.');
    }
  }

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">Command System</h1>
            <p className="mt-2 text-sm text-slate-400">
              Deterministic command routing with optional AI expansion.
            </p>
          </div>
          <button
            type="button"
            onClick={() => loadCommands(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
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

      <section className="grid gap-4 xl:grid-cols-[1fr_1.2fr]">
        <form onSubmit={submitDraft} className="panel space-y-3 p-4">
          <div className="flex items-center justify-between">
            <h2 className="text-base font-semibold text-white">
              {editingId ? 'Edit Command' : 'New Command'}
            </h2>
            {editingId ? (
              <button
                type="button"
                onClick={resetDraft}
                className="inline-flex items-center gap-1 rounded-lg border border-[rgba(255,255,255,0.18)] px-2 py-1 text-xs text-slate-300"
              >
                <X size={12} />
                Cancel
              </button>
            ) : null}
          </div>

          <label className="block text-sm">
            <span className="text-slate-300">Name</span>
            <input
              required
              value={draft.name}
              onChange={(event) => setDraft((prev) => ({ ...prev, name: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="pricing"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Description</span>
            <input
              value={draft.description}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, description: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="What this command does"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Response Text</span>
            <textarea
              required
              rows={6}
              value={draft.response_text}
              onChange={(event) =>
                setDraft((prev) => ({ ...prev, response_text: event.target.value }))
              }
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="Deterministic response body"
            />
          </label>

          <label className="block text-sm">
            <span className="text-slate-300">Tags (comma separated)</span>
            <input
              value={draft.tags}
              onChange={(event) => setDraft((prev) => ({ ...prev, tags: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-[rgba(255,255,255,0.14)] bg-[rgba(9,23,38,0.85)] px-3 py-2 text-sm text-white outline-none"
              placeholder="sales, onboarding"
            />
          </label>

          <div className="grid gap-2 sm:grid-cols-2">
            <label className="panel-soft flex items-center justify-between px-3 py-2 text-sm text-slate-300">
              Use AI
              <input
                type="checkbox"
                checked={draft.use_ai}
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, use_ai: event.target.checked }))
                }
              />
            </label>
            <label className="panel-soft flex items-center justify-between px-3 py-2 text-sm text-slate-300">
              Enabled
              <input
                type="checkbox"
                checked={draft.enabled}
                onChange={(event) =>
                  setDraft((prev) => ({ ...prev, enabled: event.target.checked }))
                }
              />
            </label>
          </div>

          <button
            type="submit"
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-lg bg-gradient-to-r from-[var(--brand-1)] to-[var(--brand-2)] px-3 py-2 text-sm font-semibold text-slate-950 disabled:opacity-60"
          >
            {editingId ? <Save size={14} /> : <Plus size={14} />}
            {saving ? 'Saving...' : editingId ? 'Update Command' : 'Create Command'}
          </button>
        </form>

        <section className="panel p-0">
          {loading ? (
            <div className="p-4 text-sm text-slate-400">Loading commands...</div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[720px] text-left text-sm">
                <thead className="border-b border-[rgba(255,255,255,0.08)] text-xs uppercase tracking-[0.14em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Mode</th>
                    <th className="px-4 py-3 font-medium">Enabled</th>
                    <th className="px-4 py-3 font-medium">Tags</th>
                    <th className="px-4 py-3 font-medium">Updated</th>
                    <th className="px-4 py-3 font-medium text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {commands.map((command) => (
                    <tr key={command.id} className="border-b border-[rgba(255,255,255,0.06)] last:border-0">
                      <td className="px-4 py-3">
                        <p className="font-medium text-white">!{command.name}</p>
                        <p className="mt-1 text-xs text-slate-400">{command.description || '-'}</p>
                      </td>
                      <td className="px-4 py-3 text-slate-300">
                        {command.use_ai ? 'AI-assisted' : 'Deterministic'}
                      </td>
                      <td className="px-4 py-3 text-slate-300">{command.enabled ? 'Yes' : 'No'}</td>
                      <td className="px-4 py-3 text-slate-400">{command.tags || '-'}</td>
                      <td className="px-4 py-3 text-slate-400">
                        {new Date(command.updated_at).toLocaleString()}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-2">
                          <button
                            type="button"
                            onClick={() => startEdit(command)}
                            className="inline-flex items-center gap-1 rounded-lg border border-[rgba(255,255,255,0.16)] px-2 py-1 text-xs text-slate-200"
                          >
                            <Pencil size={12} />
                            Edit
                          </button>
                          <button
                            type="button"
                            onClick={() => removeCommand(command)}
                            className="inline-flex items-center gap-1 rounded-lg border border-red-400/35 px-2 py-1 text-xs text-red-200"
                          >
                            <Trash2 size={12} />
                            Delete
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
      </section>
    </div>
  );
}


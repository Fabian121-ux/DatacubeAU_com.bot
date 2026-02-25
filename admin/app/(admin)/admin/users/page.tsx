'use client';

import { useEffect, useMemo, useState } from 'react';
import { Search, RefreshCw, Users, CheckCircle2, MessageSquare, Sparkles } from 'lucide-react';
import { api, type User } from '@/lib/api-client';

function formatPhone(jid: string): string {
  return jid.replace('@s.whatsapp.net', '');
}

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [total, setTotal] = useState(0);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function loadUsers(manual = false) {
    if (manual) {
      setRefreshing(true);
    }

    try {
      const response = await api.getUsers(200, 0);
      setUsers(response.users);
      setTotal(response.pagination.total);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }

  useEffect(() => {
    loadUsers();
  }, []);

  const filteredUsers = useMemo(() => {
    const term = query.trim().toLowerCase();
    if (!term) {
      return users;
    }

    return users.filter((user) => {
      return (
        formatPhone(user.jid).includes(term) ||
        (user.name || '').toLowerCase().includes(term)
      );
    });
  }, [users, query]);

  const optedInCount = useMemo(() => users.filter((user) => user.opted_in).length, [users]);

  return (
    <div className="space-y-5">
      <section className="panel p-5 md:p-6">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="section-title">User Directory</h1>
            <p className="mt-2 text-sm text-slate-400">
              Review activity and opt-in status for all WhatsApp contacts.
            </p>
          </div>

          <button
            type="button"
            onClick={() => loadUsers(true)}
            disabled={refreshing}
            className="inline-flex items-center gap-2 rounded-lg border border-[rgba(255,255,255,0.2)] bg-[rgba(7,19,32,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(32,197,165,0.5)] hover:text-white disabled:opacity-65"
          >
            <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>

        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Total</p>
            <p className="mt-2 text-2xl font-semibold text-white">{total}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Opted In</p>
            <p className="mt-2 text-2xl font-semibold text-emerald-200">{optedInCount}</p>
          </div>
          <div className="panel-soft p-3">
            <p className="text-xs uppercase tracking-[0.18em] text-slate-500">Displayed</p>
            <p className="mt-2 text-2xl font-semibold text-white">{filteredUsers.length}</p>
          </div>
        </div>

        <div className="panel-soft mt-4 flex items-center gap-3 px-3">
          <Search size={15} className="text-slate-500" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
            placeholder="Search by phone number or name"
          />
        </div>

        {error && (
          <p className="mt-4 rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
            {error}
          </p>
        )}
      </section>

      <section className="panel p-0">
        {loading ? (
          <div className="p-5 text-sm text-slate-400">Loading users...</div>
        ) : filteredUsers.length === 0 ? (
          <div className="p-5 text-sm text-slate-400">No users match your search.</div>
        ) : (
          <>
            <div className="hidden overflow-x-auto md:block">
              <table className="w-full min-w-[880px] text-left text-sm">
                <thead className="border-b border-[rgba(255,255,255,0.08)] text-xs uppercase tracking-[0.14em] text-slate-500">
                  <tr>
                    <th className="px-4 py-3 font-medium">Phone</th>
                    <th className="px-4 py-3 font-medium">Name</th>
                    <th className="px-4 py-3 font-medium">Opted In</th>
                    <th className="px-4 py-3 font-medium">Messages</th>
                    <th className="px-4 py-3 font-medium">AI Calls</th>
                    <th className="px-4 py-3 font-medium">Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredUsers.map((user) => (
                    <tr key={user.id} className="border-b border-[rgba(255,255,255,0.06)] last:border-0">
                      <td className="mono px-4 py-3 text-[13px] text-slate-200">{formatPhone(user.jid)}</td>
                      <td className="px-4 py-3 text-white">{user.name || '-'}</td>
                      <td className="px-4 py-3">
                        <span
                          className={`badge ${
                            user.opted_in
                              ? 'border-emerald-400/30 bg-emerald-500/12 text-emerald-200'
                              : 'border-slate-400/20 bg-slate-500/10 text-slate-300'
                          }`}
                        >
                          {user.opted_in ? 'Yes' : 'No'}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-slate-200">{user.message_count}</td>
                      <td className="px-4 py-3 text-slate-200">{user.ai_call_count}</td>
                      <td className="px-4 py-3 text-slate-400">{new Date(user.last_seen).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="space-y-3 p-4 md:hidden">
              {filteredUsers.map((user) => (
                <div key={user.id} className="panel-soft p-3">
                  <div className="flex items-center justify-between">
                    <p className="mono text-xs text-slate-200">{formatPhone(user.jid)}</p>
                    <span
                      className={`badge ${
                        user.opted_in
                          ? 'border-emerald-400/30 bg-emerald-500/12 text-emerald-200'
                          : 'border-slate-400/20 bg-slate-500/10 text-slate-300'
                      }`}
                    >
                      {user.opted_in ? 'Opted In' : 'Not Opted In'}
                    </span>
                  </div>
                  <p className="mt-2 text-sm text-white">{user.name || 'Unnamed user'}</p>
                  <div className="mt-3 grid grid-cols-3 gap-2 text-xs">
                    <div className="rounded-lg bg-[rgba(12,30,46,0.8)] p-2">
                      <p className="text-slate-400">Messages</p>
                      <p className="mt-1 flex items-center gap-1 text-slate-100">
                        <MessageSquare size={12} />
                        {user.message_count}
                      </p>
                    </div>
                    <div className="rounded-lg bg-[rgba(12,30,46,0.8)] p-2">
                      <p className="text-slate-400">AI Calls</p>
                      <p className="mt-1 flex items-center gap-1 text-slate-100">
                        <Sparkles size={12} />
                        {user.ai_call_count}
                      </p>
                    </div>
                    <div className="rounded-lg bg-[rgba(12,30,46,0.8)] p-2">
                      <p className="text-slate-400">Status</p>
                      <p className="mt-1 flex items-center gap-1 text-slate-100">
                        <CheckCircle2 size={12} />
                        {user.opted_in ? 'Active' : 'Idle'}
                      </p>
                    </div>
                  </div>
                  <p className="mt-3 text-xs text-slate-500">{new Date(user.last_seen).toLocaleString()}</p>
                </div>
              ))}
            </div>
          </>
        )}
      </section>
    </div>
  );
}

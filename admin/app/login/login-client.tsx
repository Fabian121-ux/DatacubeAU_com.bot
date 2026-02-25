'use client';

import { useState } from 'react';
import { useSearchParams } from 'next/navigation';
import { Lock, User, Shield, Eye, EyeOff } from 'lucide-react';

export default function LoginClientPage() {
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get('next') || '/admin';

  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password })
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({ error: 'Login failed.' }));
        throw new Error(data.error || 'Login failed.');
      }

      window.location.assign(redirectTo);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to sign in.');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="relative flex min-h-screen items-center justify-center px-4 py-10">
      <div className="panel w-full max-w-md p-6 sm:p-7">
        <div className="mb-6">
          <p className="text-xs uppercase tracking-[0.22em] text-slate-400">Datacube AU</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Private Admin Login</h1>
          <p className="mt-2 text-sm text-slate-400">
            This panel is locked for single-owner operation.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <label className="block">
            <span className="mb-2 block text-sm text-slate-300">Username</span>
            <div className="panel-soft flex items-center gap-3 px-3">
              <User size={15} className="text-slate-500" />
              <input
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                autoComplete="username"
                required
                className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
                placeholder="Owner username"
              />
            </div>
          </label>

          <label className="block">
            <span className="mb-2 block text-sm text-slate-300">Password</span>
            <div className="panel-soft flex items-center gap-3 px-3">
              <Lock size={15} className="text-slate-500" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                autoComplete="current-password"
                required
                className="w-full bg-transparent py-3 text-sm text-white outline-none placeholder:text-slate-500"
                placeholder="Your private password"
              />
              <button
                type="button"
                onClick={() => setShowPassword((value) => !value)}
                className="text-slate-400 transition hover:text-white"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
          </label>

          {error && (
            <p className="rounded-lg border border-red-400/35 bg-red-500/10 px-3 py-2 text-sm text-red-200">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="inline-flex w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[var(--brand-1)] to-[var(--brand-2)] px-4 py-3 text-sm font-semibold text-slate-950 transition hover:brightness-105 disabled:cursor-not-allowed disabled:opacity-70"
          >
            <Shield size={15} />
            {submitting ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  );
}


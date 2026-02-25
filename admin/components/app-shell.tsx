'use client';

import Link from 'next/link';
import { useEffect, useMemo, useState } from 'react';
import { usePathname } from 'next/navigation';
import clsx from 'clsx';
import {
  Bot,
  LogOut,
  Menu,
  X
} from 'lucide-react';
import { ADMIN_NAV_ITEMS } from '@/lib/nav';

const MOBILE_NAV_ITEMS = ADMIN_NAV_ITEMS.slice(0, 5);

function isActivePath(pathname: string, href: string): boolean {
  if (href === '/admin') {
    return pathname === '/admin' || pathname === '/';
  }
  return pathname.startsWith(href);
}

function NavLinks({
  pathname,
  mobile = false,
  onNavigate
}: {
  pathname: string;
  mobile?: boolean;
  onNavigate?: () => void;
}) {
  return (
    <nav className={mobile ? 'space-y-1' : 'flex items-center gap-1 overflow-x-auto'}>
      {ADMIN_NAV_ITEMS.map((item) => {
        const Icon = item.icon;
        const active = isActivePath(pathname, item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onNavigate}
            className={clsx(
              'rounded-xl px-3 py-2 text-sm transition',
              mobile ? 'flex items-center gap-3' : 'inline-flex items-center gap-2',
              active
                ? 'bg-[rgba(26,173,148,0.18)] text-white ring-1 ring-[rgba(26,173,148,0.45)]'
                : 'text-slate-300 hover:bg-[rgba(15,32,48,0.7)] hover:text-white'
            )}
          >
            <Icon size={15} />
            <span>{item.label}</span>
          </Link>
        );
      })}
    </nav>
  );
}

async function performLogout() {
  try {
    await fetch('/api/auth/logout', {
      method: 'POST',
      cache: 'no-store',
      credentials: 'include'
    });
  } finally {
    window.location.assign(`/login?logged_out=1&t=${Date.now()}`);
  }
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const activeLabel = useMemo(() => {
    const active = ADMIN_NAV_ITEMS.find((item) => isActivePath(pathname, item.href));
    return active?.label || 'Dashboard';
  }, [pathname]);

  useEffect(() => {
    setMobileMenuOpen(false);
  }, [pathname]);

  async function handleLogout() {
    setLoggingOut(true);
    await performLogout();
  }

  return (
    <div className="relative min-h-screen overflow-x-hidden bg-[var(--app-bg)] text-[var(--app-text)]">
      <div className="pointer-events-none absolute inset-0">
        <div className="absolute -left-20 top-[-120px] h-[280px] w-[280px] rounded-full bg-[rgba(24,167,143,0.22)] blur-3xl" />
        <div className="absolute right-[-120px] top-[120px] h-[320px] w-[320px] rounded-full bg-[rgba(255,165,81,0.15)] blur-3xl" />
      </div>

      <header className="sticky top-0 z-40 border-b border-[rgba(255,255,255,0.08)] bg-[rgba(4,11,20,0.86)] backdrop-blur-xl">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 md:px-6">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-gradient-to-br from-[var(--brand-1)] to-[var(--brand-2)] text-slate-950">
              <Bot size={20} />
            </div>
            <div className="min-w-0">
              <p className="text-[11px] uppercase tracking-[0.24em] text-slate-400">Datacube AU</p>
              <p className="truncate text-base font-semibold text-white">WhatsApp Control Panel</p>
            </div>
          </div>

          <div className="hidden min-w-0 flex-1 justify-center md:flex">
            <div className="max-w-full">
              <NavLinks pathname={pathname} />
            </div>
          </div>

          <div className="flex items-center gap-2">
            <span className="hidden rounded-full border border-[rgba(255,255,255,0.15)] bg-[rgba(9,23,38,0.88)] px-3 py-1 text-xs text-slate-300 md:inline-flex">
              {activeLabel}
            </span>
            <button
              type="button"
              onClick={handleLogout}
              disabled={loggingOut}
              className="hidden items-center gap-2 rounded-xl border border-[rgba(255,255,255,0.18)] bg-[rgba(6,16,28,0.9)] px-3 py-2 text-xs font-medium text-slate-200 transition hover:border-[rgba(26,173,148,0.55)] hover:text-white disabled:cursor-not-allowed disabled:opacity-60 md:inline-flex"
            >
              <LogOut size={14} />
              {loggingOut ? 'Signing out...' : 'Sign out'}
            </button>
            <button
              type="button"
              onClick={() => setMobileMenuOpen((open) => !open)}
              className="inline-flex items-center justify-center rounded-lg border border-[rgba(255,255,255,0.18)] bg-[rgba(6,16,28,0.9)] p-2 text-slate-200 md:hidden"
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? <X size={18} /> : <Menu size={18} />}
            </button>
          </div>
        </div>
      </header>

      <div className="mx-auto grid max-w-7xl gap-4 px-4 py-5 pb-24 md:gap-6 md:px-6 md:py-8 md:pb-8 xl:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="hidden h-fit rounded-2xl border border-[rgba(255,255,255,0.1)] bg-[rgba(6,16,28,0.7)] p-4 shadow-[0_16px_50px_rgba(0,0,0,0.25)] xl:sticky xl:top-24 xl:block">
          <NavLinks pathname={pathname} mobile />
          <div className="mt-4 rounded-xl border border-[rgba(255,255,255,0.08)] bg-[rgba(8,21,35,0.75)] p-3 text-xs text-slate-300">
            <p className="font-medium text-white">Private Mode</p>
            <p className="mt-1 leading-relaxed text-slate-400">
              Single-user access is enabled with secure cookie sessions.
            </p>
          </div>
        </aside>

        <main className="min-w-0">
          <div className="animate-in fade-in duration-300">{children}</div>
        </main>
      </div>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-30 bg-[rgba(3,8,14,0.6)] backdrop-blur-sm md:hidden">
          <div className="absolute left-0 top-[57px] w-full border-b border-[rgba(255,255,255,0.08)] bg-[rgba(4,11,20,0.98)] p-4">
            <NavLinks pathname={pathname} mobile onNavigate={() => setMobileMenuOpen(false)} />
            <button
              type="button"
              onClick={handleLogout}
              disabled={loggingOut}
              className="mt-3 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-[rgba(255,255,255,0.18)] bg-[rgba(6,16,28,0.95)] px-3 py-2 text-sm font-medium text-slate-200 disabled:cursor-not-allowed disabled:opacity-60"
            >
              <LogOut size={14} />
              {loggingOut ? 'Signing out...' : 'Sign out'}
            </button>
          </div>
        </div>
      )}

      <nav className="fixed inset-x-0 bottom-0 z-30 border-t border-[rgba(255,255,255,0.08)] bg-[rgba(4,11,20,0.96)] px-2 py-2 backdrop-blur-xl md:hidden">
        <div className="flex items-center justify-around">
          {MOBILE_NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActivePath(pathname, item.href);
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  'flex min-w-[56px] flex-col items-center rounded-lg px-2 py-1 text-[11px]',
                  active ? 'text-[var(--brand-1)]' : 'text-slate-400'
                )}
              >
                <Icon size={16} />
                <span className="mt-1">{item.label}</span>
              </Link>
            );
          })}
        </div>
      </nav>
    </div>
  );
}

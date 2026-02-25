import { NextResponse } from 'next/server';
import {
  ADMIN_SESSION_COOKIE,
  SESSION_TTL_SECONDS,
  buildSessionValue,
  getConfiguredCredentials
} from '@/lib/auth';

interface LoginBody {
  username?: string;
  password?: string;
}

interface AttemptState {
  failures: number;
  windowStartedAt: number;
  blockedUntil: number;
}

const LOGIN_ATTEMPTS = new Map<string, AttemptState>();
const MAX_FAILURES = Number.parseInt(process.env.ADMIN_LOGIN_MAX_ATTEMPTS || '5', 10);
const WINDOW_MS = Number.parseInt(process.env.ADMIN_LOGIN_WINDOW_MS || String(15 * 60 * 1000), 10);
const BLOCK_MS = Number.parseInt(process.env.ADMIN_LOGIN_BLOCK_MS || String(30 * 60 * 1000), 10);

function getClientIp(request: Request): string {
  const forwarded = request.headers.get('x-forwarded-for');
  if (forwarded) {
    const firstIp = forwarded.split(',')[0]?.trim();
    if (firstIp) {
      return firstIp;
    }
  }

  const realIp = request.headers.get('x-real-ip');
  if (realIp) {
    return realIp;
  }

  return 'unknown';
}

function cleanupAttempts(now: number) {
  LOGIN_ATTEMPTS.forEach((state, key) => {
    const expiredWindow = now - state.windowStartedAt > WINDOW_MS;
    const isBlocked = state.blockedUntil > 0;
    const lockExpired = isBlocked && state.blockedUntil <= now;

    if ((!isBlocked && expiredWindow) || (lockExpired && expiredWindow)) {
      LOGIN_ATTEMPTS.delete(key);
    }
  });
}

function getAttemptKey(ip: string, username: string): string {
  return `${ip}:${username.toLowerCase()}`;
}

function getBlockState(key: string, now: number): { blocked: boolean; retryAfterSec: number } {
  const state = LOGIN_ATTEMPTS.get(key);
  if (!state) {
    return { blocked: false, retryAfterSec: 0 };
  }

  if (state.blockedUntil > now) {
    return {
      blocked: true,
      retryAfterSec: Math.max(1, Math.ceil((state.blockedUntil - now) / 1000))
    };
  }

  return { blocked: false, retryAfterSec: 0 };
}

function registerFailure(key: string, now: number): { blocked: boolean; retryAfterSec: number } {
  const current = LOGIN_ATTEMPTS.get(key);

  if (!current || now - current.windowStartedAt > WINDOW_MS) {
    LOGIN_ATTEMPTS.set(key, {
      failures: 1,
      windowStartedAt: now,
      blockedUntil: 0
    });
    return { blocked: false, retryAfterSec: 0 };
  }

  const nextFailures = current.failures + 1;
  if (nextFailures >= MAX_FAILURES) {
    const blockedUntil = now + BLOCK_MS;
    LOGIN_ATTEMPTS.set(key, {
      failures: 0,
      windowStartedAt: now,
      blockedUntil
    });
    return {
      blocked: true,
      retryAfterSec: Math.max(1, Math.ceil(BLOCK_MS / 1000))
    };
  }

  LOGIN_ATTEMPTS.set(key, {
    failures: nextFailures,
    windowStartedAt: current.windowStartedAt,
    blockedUntil: 0
  });

  return { blocked: false, retryAfterSec: 0 };
}

function clearFailures(key: string) {
  LOGIN_ATTEMPTS.delete(key);
}

export async function POST(request: Request) {
  const credentials = getConfiguredCredentials();
  if (!credentials.password) {
    return NextResponse.json(
      {
        error: 'Login is not configured. Set ADMIN_LOGIN_PASSWORD or ADMIN_TOKEN in admin environment.'
      },
      { status: 500 }
    );
  }

  let body: LoginBody;
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: 'Invalid request payload.' }, { status: 400 });
  }

  const username = (body.username || '').trim();
  const password = body.password || '';
  const now = Date.now();
  const ip = getClientIp(request);
  const attemptKey = getAttemptKey(ip, username || 'unknown');

  cleanupAttempts(now);

  const blockState = getBlockState(attemptKey, now);
  if (blockState.blocked) {
    return NextResponse.json(
      { error: `Too many login attempts. Try again in ${blockState.retryAfterSec} seconds.` },
      {
        status: 429,
        headers: {
          'Retry-After': String(blockState.retryAfterSec)
        }
      }
    );
  }

  const usernameMatches = username.toLowerCase() === credentials.username.toLowerCase();
  const passwordMatches = password === credentials.password;

  if (!usernameMatches || !passwordMatches) {
    const failureState = registerFailure(attemptKey, now);
    if (failureState.blocked) {
      return NextResponse.json(
        { error: `Too many login attempts. Try again in ${failureState.retryAfterSec} seconds.` },
        {
          status: 429,
          headers: {
            'Retry-After': String(failureState.retryAfterSec)
          }
        }
      );
    }

    return NextResponse.json({ error: 'Invalid username or password.' }, { status: 401 });
  }

  clearFailures(attemptKey);

  const response = NextResponse.json({ ok: true });
  response.cookies.set({
    name: ADMIN_SESSION_COOKIE,
    value: buildSessionValue(username),
    httpOnly: true,
    sameSite: 'strict',
    secure: process.env.NODE_ENV === 'production',
    path: '/',
    maxAge: SESSION_TTL_SECONDS
  });

  return response;
}

import { createHmac, timingSafeEqual } from 'crypto';
import type { NextRequest } from 'next/server';
import { cookies } from 'next/headers';

export const ADMIN_SESSION_COOKIE = 'datacube_admin_session';
export const SESSION_TTL_SECONDS = 60 * 60 * 24 * 14; // 14 days
const DEFAULT_ADMIN_USERNAME = 'croneX11!';
const DEFAULT_ADMIN_PASSWORD = 'factzina11!';

interface SessionData {
  username: string;
  expiresAt: number;
}

export interface AdminCredentials {
  username: string;
  password: string | null;
}

function safeCompare(a: string, b: string): boolean {
  const left = Buffer.from(a);
  const right = Buffer.from(b);

  if (left.length !== right.length) {
    return false;
  }

  return timingSafeEqual(left, right);
}

function getSessionSecret(): string {
  return (
    process.env.ADMIN_SESSION_SECRET ||
    process.env.NEXTAUTH_SECRET ||
    process.env.ADMIN_TOKEN ||
    'local-dev-session-secret'
  );
}

function sign(payload: string): string {
  return createHmac('sha256', getSessionSecret()).update(payload).digest('hex');
}

export function getConfiguredCredentials(): AdminCredentials {
  const username = (process.env.ADMIN_LOGIN_USERNAME || DEFAULT_ADMIN_USERNAME).trim() || DEFAULT_ADMIN_USERNAME;
  const password = (process.env.ADMIN_LOGIN_PASSWORD || DEFAULT_ADMIN_PASSWORD).trim();

  return {
    username,
    password: password || null
  };
}

export function buildSessionValue(username: string): string {
  const encodedUsername = encodeURIComponent(username);
  const expiresAt = Date.now() + SESSION_TTL_SECONDS * 1000;
  const payload = `${encodedUsername}.${expiresAt}`;
  const signature = sign(payload);
  return `${payload}.${signature}`;
}

export function verifySessionValue(rawValue?: string | null): SessionData | null {
  if (!rawValue) {
    return null;
  }

  const firstDot = rawValue.indexOf('.');
  const lastDot = rawValue.lastIndexOf('.');

  if (firstDot <= 0 || lastDot <= firstDot) {
    return null;
  }

  const encodedUsername = rawValue.slice(0, firstDot);
  const expiresAtRaw = rawValue.slice(firstDot + 1, lastDot);
  const signature = rawValue.slice(lastDot + 1);

  const expiresAt = Number.parseInt(expiresAtRaw, 10);
  if (!Number.isFinite(expiresAt) || expiresAt < Date.now()) {
    return null;
  }

  const payload = `${encodedUsername}.${expiresAt}`;
  const expected = sign(payload);

  if (!safeCompare(signature, expected)) {
    return null;
  }

  let username = encodedUsername;
  try {
    username = decodeURIComponent(encodedUsername);
  } catch {
    return null;
  }

  return { username, expiresAt };
}

export function isRequestAuthenticated(request: NextRequest): boolean {
  const session = verifySessionValue(request.cookies.get(ADMIN_SESSION_COOKIE)?.value);
  return Boolean(session);
}

export function getSessionFromCookies(): SessionData | null {
  const store = cookies();
  return verifySessionValue(store.get(ADMIN_SESSION_COOKIE)?.value);
}

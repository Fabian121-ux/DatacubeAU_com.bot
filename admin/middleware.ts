import { NextResponse, type NextRequest } from 'next/server';

const ADMIN_SESSION_COOKIE = 'datacube_admin_session';
const SESSION_SECRET =
  process.env.ADMIN_SESSION_SECRET ||
  process.env.NEXTAUTH_SECRET ||
  process.env.ADMIN_TOKEN ||
  'local-dev-session-secret';

const PUBLIC_ROUTES = new Set([
  '/login',
  '/api/auth/login',
  '/api/auth/logout'
]);

function isPublicPath(pathname: string): boolean {
  if (PUBLIC_ROUTES.has(pathname)) {
    return true;
  }

  if (pathname.startsWith('/_next/')) {
    return true;
  }

  if (pathname === '/favicon.ico') {
    return true;
  }

  return false;
}

function toHex(buffer: ArrayBuffer): string {
  return Array.from(new Uint8Array(buffer))
    .map((value) => value.toString(16).padStart(2, '0'))
    .join('');
}

async function signPayload(payload: string): Promise<string> {
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(SESSION_SECRET),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign(
    'HMAC',
    key,
    new TextEncoder().encode(payload)
  );

  return toHex(signature);
}

async function hasValidSession(request: NextRequest): Promise<boolean> {
  const raw = request.cookies.get(ADMIN_SESSION_COOKIE)?.value;
  if (!raw) {
    return false;
  }

  const firstDot = raw.indexOf('.');
  const lastDot = raw.lastIndexOf('.');

  if (firstDot <= 0 || lastDot <= firstDot) {
    return false;
  }

  const encodedUsername = raw.slice(0, firstDot);
  const expiresRaw = raw.slice(firstDot + 1, lastDot);
  const signature = raw.slice(lastDot + 1);

  const expiresAt = Number.parseInt(expiresRaw, 10);
  if (!Number.isFinite(expiresAt) || expiresAt <= Date.now()) {
    return false;
  }

  const payload = `${encodedUsername}.${expiresAt}`;
  const expected = await signPayload(payload);
  return signature === expected;
}

export async function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl;
  const authenticated = await hasValidSession(request);

  if (isPublicPath(pathname)) {
    if (pathname === '/login' && authenticated) {
      return NextResponse.redirect(new URL('/admin', request.url));
    }
    return NextResponse.next();
  }

  if (authenticated) {
    return NextResponse.next();
  }

  if (pathname.startsWith('/api/')) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const loginUrl = new URL('/login', request.url);
  loginUrl.searchParams.set('next', `${pathname}${search}`);
  return NextResponse.redirect(loginUrl);
}

export const config = {
  matcher: ['/((?!_next/static|_next/image).*)']
};

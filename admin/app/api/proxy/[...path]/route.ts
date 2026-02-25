import { NextResponse, type NextRequest } from 'next/server';
import { ADMIN_SESSION_COOKIE, verifySessionValue } from '@/lib/auth';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL || process.env.ADMIN_API_BASE_URL || 'http://localhost:3001';

function buildUpstreamUrl(request: NextRequest, path: string[]): URL {
  const [firstSegment] = path;
  const directRoots = new Set(['bot', 'admin']);

  const pathname = directRoots.has(firstSegment)
    ? `/${path.join('/')}`
    : `/api/v1/${path.join('/')}`;

  const upstream = new URL(pathname, API_BASE_URL);
  upstream.search = request.nextUrl.search;
  return upstream;
}

function buildHeaders(request: NextRequest, adminToken: string): Headers {
  const headers = new Headers();
  const contentType = request.headers.get('content-type');
  if (contentType) {
    headers.set('content-type', contentType);
  }
  headers.set('authorization', `Bearer ${adminToken}`);
  return headers;
}

async function fetchWithTimeout(url: string, init: RequestInit, timeoutMs: number): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { ...init, signal: controller.signal });
  } finally {
    clearTimeout(timer);
  }
}

async function handleProxy(request: NextRequest, context: { params: { path: string[] } }) {
  const session = verifySessionValue(request.cookies.get(ADMIN_SESSION_COOKIE)?.value);
  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  const adminToken =
    process.env.ADMIN_API_TOKEN || process.env.ADMIN_TOKEN || process.env.API_SECRET_KEY;
  if (!adminToken) {
    return NextResponse.json(
      { error: 'ADMIN token is not configured in the admin environment.' },
      { status: 500 }
    );
  }

  const path = context.params.path || [];
  const upstreamUrl = buildUpstreamUrl(request, path);

  const init: RequestInit = {
    method: request.method,
    headers: buildHeaders(request, adminToken),
    cache: 'no-store'
  };

  if (!['GET', 'HEAD'].includes(request.method)) {
    init.body = await request.text();
  }

  const timeoutMs = Number.parseInt(process.env.ADMIN_PROXY_TIMEOUT_MS || '15000', 10);
  let upstreamResponse: Response;
  try {
    upstreamResponse = await fetchWithTimeout(upstreamUrl.toString(), init, timeoutMs);
  } catch (error) {
    try {
      upstreamResponse = await fetchWithTimeout(upstreamUrl.toString(), init, timeoutMs);
    } catch (retryError) {
      const message = retryError instanceof Error ? retryError.message : 'Unknown upstream error';
      return NextResponse.json(
        { error: `Failed to reach API server: ${message}` },
        { status: 502 }
      );
    }
  }

  const body = await upstreamResponse.text();
  const responseHeaders = new Headers();
  const contentType = upstreamResponse.headers.get('content-type');
  if (contentType) responseHeaders.set('content-type', contentType);

  return new NextResponse(body, {
    status: upstreamResponse.status,
    headers: responseHeaders
  });
}

export const dynamic = 'force-dynamic';

export async function GET(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function POST(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function PUT(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function PATCH(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

export async function DELETE(request: NextRequest, context: { params: { path: string[] } }) {
  return handleProxy(request, context);
}

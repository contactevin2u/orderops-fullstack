import { API_BASE } from '../config/env';

export interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  data?: T;
  error?: string;
}

type TokenGetter = () => Promise<string | undefined>;

let getToken: TokenGetter = async () => undefined;

export function setTokenGetter(fn: TokenGetter) {
  getToken = fn;
}

async function request(path: string, opts: RequestInit = {}, extraHeaders?: Record<string, string>): Promise<ApiResponse> {
  const headers: Record<string, string> = { ...(extraHeaders || {}), ...(opts.headers as Record<string, string>) };
  try {
    const token = await getToken();
    if (token) headers['Authorization'] = `Bearer ${token}`;
  } catch {}
  try {
    const res = await fetch(`${API_BASE}${path}`, { ...opts, headers });
    const ct = res.headers.get('content-type');
    let data: any = undefined;
    if (ct && ct.includes('application/json')) {
      data = await res.json();
    } else {
      data = await res.text();
    }
    if (res.ok) return { ok: true, status: res.status, data };
    const err = typeof data === 'string' ? data : data?.error;
    return { ok: false, status: res.status, error: err };
  } catch (e: any) {
    return { ok: false, status: 0, error: e?.message ?? String(e) };
  }
}

export const api = {
  get: (path: string, headers?: Record<string, string>) => request(path, { method: 'GET' }, headers),
  post: (path: string, body?: any, headers?: Record<string, string>) =>
    request(
      path,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      },
      headers,
    ),
  patch: (path: string, body?: any, headers?: Record<string, string>) =>
    request(
      path,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      },
      headers,
    ),
  delete: (path: string, headers?: Record<string, string>) => request(path, { method: 'DELETE' }, headers),
  upload: (path: string, body: FormData, headers?: Record<string, string>) =>
    request(
      path,
      {
        method: 'POST',
        body,
      },
      headers,
    ),
};


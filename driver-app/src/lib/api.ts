import { API_BASE } from '../config/env';

export interface ApiResponse<T = any> {
  ok: boolean;
  status: number;
  data?: T;
  error?: string;
}

async function request(path: string, opts: RequestInit = {}, idToken?: string): Promise<ApiResponse> {
  const headers: Record<string, string> = {
    ...(opts.headers as Record<string, string>),
  };
  if (idToken) headers['Authorization'] = `Bearer ${idToken}`;
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
    return { ok: false, status: res.status, error: (data && data.error) || (typeof data === 'string' ? data : undefined) };
  } catch (e: any) {
    return { ok: false, status: 0, error: e?.message ?? String(e) };
  }
}

export const api = {
  get: (path: string, idToken?: string) => request(path, { method: 'GET' }, idToken),
  post: (path: string, idToken: string, body?: any) =>
    request(
      path,
      {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      },
      idToken,
    ),
  patch: (path: string, idToken: string, body?: any) =>
    request(
      path,
      {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: body ? JSON.stringify(body) : undefined,
      },
      idToken,
    ),
  upload: (path: string, idToken: string, body: FormData) =>
    request(
      path,
      {
        method: 'POST',
        body,
      },
      idToken,
    ),
};

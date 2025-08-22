// utils/api.ts
export type Json = Record<string, any> | any[];

function normalizeBase(s?: string) {
  if (!s) return "";
  return s.replace(/\/+$/, "");
}

const ENV_BASE = normalizeBase(process.env.NEXT_PUBLIC_API_URL);
// When next.config.js rewrites are active, API_BASE can be "/_api"
const API_BASE = ENV_BASE || "/_api";

function pathJoin(p: string) {
  return `${API_BASE}${p.startsWith("/") ? p : `/${p}`}`;
}

async function request<T = any>(
  path: string,
  init?: RequestInit & { json?: any }
): Promise<T> {
  const { json, headers, ...rest } = init || {};
  const res = await fetch(pathJoin(path), {
    method: json ? "POST" : (rest.method || "GET"),
    headers: {
      Accept: "application/json",
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...(headers || {}),
    },
    body: json ? JSON.stringify(json) : rest.body,
    ...rest,
  }).catch((e: any) => {
    throw new Error(`Network error calling ${path}: ${e?.message || "failed to fetch"}`);
  });

  const text = await res.text();
  const isJSON = res.headers.get("content-type")?.includes("application/json");
  const data: any = isJSON && text ? JSON.parse(text) : text;

  if (!res.ok) {
    const msg =
      (isJSON && (data?.detail || data?.message)) ||
      (typeof data === "string" && data) ||
      res.statusText;
    const err: any = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data as T;
}

// -------- Health
export function ping() {
  return request<{ ok: boolean } | string>("/healthz");
}

// -------- Parse
export function parseMessage(text: string) {
  return request<Json>("/parse", { json: { text, message: text } });
}

// -------- Orders (normalized)
export type Order = {
  id: number;
  code?: string;
  type?: string;
  status?: string;
  total?: number;
  paid_amount?: number;
  balance?: number;
};

type OrdersList = { items: Order[]; total?: number };

export async function listOrders(
  q?: string,
  status?: string,
  type?: string
): Promise<OrdersList> {
  const sp = new URLSearchParams();
  if (q) sp.set("q", q);
  if (status) sp.set("status", status);
  if (type) sp.set("type", type);
  const qs = sp.toString();

  const data = await request<any>(`/orders${qs ? `?${qs}` : ""}`);
  // Normalize: backend may return array or { items, total }
  if (Array.isArray(data)) return { items: data as Order[], total: data.length };
  if (data && typeof data === "object") {
    const items = Array.isArray(data.items) ? (data.items as Order[]) : [];
    const total =
      typeof data.total === "number"
        ? data.total
        : (Array.isArray(data.items) ? data.items.length : undefined);
    return { items, total };
  }
  return { items: [], total: 0 };
}

export function getOrder(id: number | string) {
  return request<any>(`/orders/${id}`);
}

// Optional: tweak parsed payload before posting if your parser is loose
function normalizeParsedForOrder(input: any) {
  if (!input) return input;
  // many backends return { ok, parsed }; accept both shapes safely
  const parsed = input?.parsed ? input.parsed : input;

  // Allow both "code" or "sku" mixups; do NOT force if already correct
  if (parsed?.order) {
    const order = parsed.order;
    // If someone put order code into first item.sku by mistake, you could move it back here
    // but only when order.code is empty.
    if (!order.code && Array.isArray(order.items) && order.items.length) {
      const guess = order.items.find((it: any) => it?.sku && typeof it.sku === "string");
      if (guess && /^[A-Za-z]{1,3}\d{3,5}$/.test(guess.sku)) {
        order.code = guess.sku;
        guess.sku = null;
      }
    }
  }
  return parsed;
}

export async function createOrderFromParsed(parsed: any) {
  const normalized = normalizeParsedForOrder(parsed);
  const payload = normalized?.parsed ? normalized.parsed : normalized;

  const customer = payload?.customer;
  const order = payload?.order;

  if (!customer || !order) {
    throw new Error("Parsed payload missing {customer, order}. Please re-parse or edit JSON.");
  }

  try {
    // Primary: top-level {customer, order}
    return await request<any>("/orders", { json: { customer, order } });
  } catch (e: any) {
    // Fallback: some backends accept { parsed: { customer, order } }
    if (e?.status === 422 || e?.status === 400) {
      return request<any>("/orders", { json: { parsed: { customer, order } } });
    }
    throw e;
  }
}

export function createManualOrder(payload: { customer: any; order: any }) {
  return request<any>("/orders", { json: payload });
}

export function updateOrder(id: number, patch: any) {
  return request<any>(`/orders/${id}`, { method: "PATCH", json: patch }).catch((e: any) => {
    if (e?.status === 405) return request<any>(`/orders/${id}`, { method: "PUT", json: patch });
    throw e;
  });
}

export async function voidOrder(id: number, reason?: string) {
  try {
    return await request<any>(`/orders/${id}/void`, { json: { reason } });
  } catch (e1: any) {
    if (e1?.status === 404 || e1?.status === 405) {
      try {
        return await request<any>(`/orders/${id}/cancel`, { json: { reason } });
      } catch (e2: any) {
        if (e2?.status === 404 || e2?.status === 405)
          return await updateOrder(id, { status: "CANCELLED", cancel_reason: reason || "" });
        throw e2;
      }
    }
    throw e1;
  }
}

export function markReturned(id: number, date?: string) {
  const body: any = {};
  if (date) body.date = date;
  return request<any>(`/orders/${id}/return`, { json: body });
}

export function markBuyback(id: number, amount: number) {
  return request<any>(`/orders/${id}/buyback`, { json: { amount } });
}

export function orderDue(id: number, asOf?: string) {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request<any>(`/orders/${id}/due${qs}`);
}

// -------- Payments
export function addPayment(payload: {
  order_id: number;
  amount: number;
  date?: string;
  method?: string;
  reference?: string;
  category?: string;
}) {
  return request<any>("/payments", { json: payload });
}
export function voidPayment(paymentId: number, reason?: string) {
  return request<any>(`/payments/${paymentId}/void`, { json: { reason } });
}

// -------- Reports
export function outstanding(type?: "INSTALLMENT" | "RENTAL") {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return request<{ items: any[] }>(`/reports/outstanding${qs}`);
}

// -------- Documents
export function invoicePdfUrl(orderId: number) {
  const base = API_BASE;
  return `${base}/documents/invoice/${orderId}.pdf`;
}

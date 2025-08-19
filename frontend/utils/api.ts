// frontend/utils/api.ts
export type Json = Record<string, any> | any[];

function normalizeBase(s?: string) {
  if (!s) return "";
  return s.replace(/\/+$/, "");
}

const ENV_BASE = normalizeBase(process.env.NEXT_PUBLIC_API_URL);
// If ENV is not set, we'll proxy via /_api (see next.config.js rewrite below)
const API_BASE = ENV_BASE || "/_api";

function pathJoin(p: string) {
  return `${API_BASE}${p.startsWith("/") ? p : `/${p}`}`;
}

async function request<T = any>(path: string, init?: RequestInit & { json?: any }): Promise<T> {
  const { json, headers, ...rest } = init || {};
  let res: Response;
  try {
    res = await fetch(pathJoin(path), {
      method: json ? "POST" : (rest.method || "GET"),
      headers: {
        Accept: "application/json",
        ...(json ? { "Content-Type": "application/json" } : {}),
        ...(headers || {}),
      },
      body: json ? JSON.stringify(json) : rest.body,
      ...rest,
    });
  } catch (e: any) {
    // Make "failed to fetch" easier to diagnose
    throw new Error(`Network error calling ${path}: ${e?.message || "failed to fetch"}`);
  }

  const contentType = res.headers.get("content-type") || "";
  const isJSON = contentType.includes("application/json");
  const text = await res.text();
  let data: any;
  try {
    data = isJSON && text ? JSON.parse(text) : text;
  } catch {
    data = text;
  }

  if (!res.ok) {
    const msg =
      (isJSON && (data?.detail || data?.message)) ||
      (typeof data === "string" && data) ||
      res.statusText ||
      `HTTP ${res.status}`;
    const err: any = new Error(typeof msg === "string" ? msg : JSON.stringify(msg));
    err.status = res.status;
    err.data = data;
    throw err;
  }
  return data as T;
}

// Health
export function ping() {
  return request<{ ok: boolean } | string>("/healthz");
}

// Parse – send both keys for compatibility
export function parseMessage(text: string) {
  return request<Json>("/parse", { json: { text, message: text } });
}

/** Helpers to normalize various backend response shapes into { items, total } */
function asList(result: any): { items: any[]; total: number } {
  if (Array.isArray(result)) return { items: result, total: result.length };
  if (Array.isArray(result?.items)) return { items: result.items, total: result.total ?? result.items.length };
  if (Array.isArray(result?.data)) return { items: result.data, total: result.total ?? result.data.length };
  // last resort: wrap single object or return empty
  if (result && typeof result === "object") return { items: [result], total: 1 };
  return { items: [], total: 0 };
}

// Orders
export async function listOrders(q?: string, status?: string, type?: string) {
  const sp = new URLSearchParams();
  if (q) sp.set("q", q);
  if (status) sp.set("status", status);
  if (type) sp.set("type", type);
  const qs = sp.toString();
  const raw = await request<any>(`/orders${qs ? `?${qs}` : ""}`);
  return asList(raw); // tolerant to array or {items}
}

export function getOrder(id: number | string) {
  return request<any>(`/orders/${id}`);
}

export async function createOrderFromParsed(parsed: Json) {
  // Prefer the common backend contract: { parsed: ... }
  try {
    return await request<any>("/orders", { json: { parsed } });
  } catch (e: any) {
    // Fallback to raw body if the backend accepts it directly
    if (e?.status === 400 || e?.status === 422) {
      return await request<any>("/orders", { json: parsed });
    }
    throw e;
  }
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
        if (e2?.status === 404 || e2?.status === 405) return await updateOrder(id, { status: "CANCELLED", cancel_reason: reason || "" });
        throw e2;
      }
    }
    throw e1;
  }
}

export function markReturned(id: number, date?: string) {
  return request<any>(`/orders/${id}/return`, { json: { date } });
}
export function markBuyback(id: number, amount: number) {
  return request<any>(`/orders/${id}/buyback`, { json: { amount } });
}

// Payments
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

// Reports
export async function outstanding(type?: "INSTALLMENT" | "RENTAL") {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  const raw = await request<any>(`/reports/outstanding${qs}`);
  return asList(raw); // tolerant to array or {items}
}

// Documents – use absolute API if available so PDFs open in a new tab even without the proxy
export function invoicePdfUrl(orderId: number) {
  const base = ENV_BASE || "/_api";
  return `${base}/documents/invoice/${orderId}.pdf`;
}

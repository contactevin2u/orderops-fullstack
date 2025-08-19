export type Json = Record<string, any> | any[];

function normalizeBase(s?: string) {
  if (!s) return "";
  return s.replace(/\/+$/, "");
}

const ENV_BASE = normalizeBase(process.env.NEXT_PUBLIC_API_URL);
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
    throw new Error(
      `Network error calling ${path}: ${e?.message || "failed to fetch"}`
    );
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

// ---------- Helpers ----------
/** Accepts whatever /parse returns and produces {customer, order} */
export function normalizeParsedForOrder(input: any) {
  // unwrap { ok, parsed } or { parsed }
  const payload = input && typeof input === "object" && "parsed" in input
    ? (input as any).parsed
    : input;

  // Some backends might nest under 'data'
  const core = payload && payload.data ? payload.data : payload;

  // If somehow customer/order are one level deeper, attempt to surface them
  if (core?.customer && core?.order) return { customer: core.customer, order: core.order };

  // If parse returned only order details, try to split
  if (!core?.customer && (core?.order || core?.items)) {
    return { customer: core.customer || {}, order: core.order || core };
  }

  return core; // best effort; caller will still validate
}

// ---------- Health ----------
export function ping() {
  return request<{ ok: boolean } | string>("/healthz");
}

// ---------- Parse ----------
export function parseMessage(text: string) {
  // Compatible with either backends expecting {text} or {message}
  return request<Json>("/parse", { json: { text, message: text } });
}

// ---------- Orders ----------
export function listOrders(q?: string, status?: string, type?: string) {
  const sp = new URLSearchParams();
  if (q) sp.set("q", q);
  if (status) sp.set("status", status);
  if (type) sp.set("type", type);
  const qs = sp.toString();
  return request<{ items?: any[]; total?: number } | any[]>(`/orders${qs ? `?${qs}` : ""}`);
}

export function getOrder(id: number | string) {
  return request<any>(`/orders/${id}`);
}

/**
 * Accepts either:
 *  - {customer, order}
 *  - {ok, parsed: {customer, order}}
 *  - {parsed: {customer, order}}
 * and posts the correct shape to the backend.
 */
export async function createOrderFromParsed(parsed: any) {
  const normalized = normalizeParsedForOrder(parsed);

  // Hard-validate shape before POST
  const customer = normalized?.customer;
  const order = normalized?.order;

  if (!customer || !order) {
    throw new Error(
      "Parsed payload missing {customer, order}. Please re-parse the message."
    );
  }

  try {
    // Primary: top-level {customer, order}
    return await request<any>("/orders", { json: { customer, order } });
  } catch (e: any) {
    // Fallback: some backends accept {parsed: {...}}
    if (e?.status === 422 || e?.status === 400) {
      return request<any>("/orders", { json: { parsed: { customer, order } } });
    }
    throw e;
  }
}

export function updateOrder(id: number, patch: any) {
  return request<any>(`/orders/${id}`, { method: "PATCH", json: patch }).catch(
    (e: any) => {
      if (e?.status === 405)
        return request<any>(`/orders/${id}`, { method: "PUT", json: patch });
      throw e;
    }
  );
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
          return await updateOrder(id, {
            status: "CANCELLED",
            cancel_reason: reason || "",
          });
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

// ---------- Payments ----------
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

// ---------- Reports ----------
export function outstanding(type?: "INSTALLMENT" | "RENTAL") {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return request<{ items: any[] } | any[]>(`/reports/outstanding${qs}`);
}

// ---------- Documents ----------
export function invoicePdfUrl(orderId: number) {
  const base = API_BASE;
  return `${base}/documents/invoice/${orderId}.pdf`;
}

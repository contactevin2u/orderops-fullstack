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

// Enhanced error messages for better user experience
function getUserFriendlyErrorMessage(status: number, path: string, serverMessage?: string): string {
  // Network/connectivity errors
  if (status === 0 || !status) {
    return "Unable to connect to server. Please check your internet connection and try again.";
  }
  
  // Authentication errors
  if (status === 401) {
    return "Your session has expired. Please sign in again to continue.";
  }
  
  if (status === 403) {
    return "You don't have permission to perform this action. Please contact your administrator.";
  }
  
  // Not found errors
  if (status === 404) {
    if (path.includes('/orders/')) return "Order not found. It may have been deleted or moved.";
    if (path.includes('/drivers/')) return "Driver not found. They may have been removed from the system.";
    if (path.includes('/payments/')) return "Payment record not found.";
    return "The requested item could not be found.";
  }
  
  // Validation errors
  if (status === 400) {
    if (serverMessage) {
      // Make server validation messages more user-friendly
      if (serverMessage.includes('required')) return "Please fill in all required fields and try again.";
      if (serverMessage.includes('invalid')) return "Please check your input and correct any errors.";
      if (serverMessage.includes('duplicate')) return "This item already exists. Please use a different value.";
      return serverMessage;
    }
    return "There was an error with your request. Please check your input and try again.";
  }
  
  // Conflict errors
  if (status === 409) {
    return "This action conflicts with existing data. Please refresh and try again.";
  }
  
  // Unprocessable entity
  if (status === 422) {
    return "The information provided is not valid. Please review and correct your input.";
  }
  
  // Rate limiting
  if (status === 429) {
    return "Too many requests. Please wait a moment and try again.";
  }
  
  // Server errors
  if (status >= 500) {
    return "The server encountered an error. Please try again in a few moments or contact support if the problem persists.";
  }
  
  // Fallback for any other status codes
  return serverMessage || `An unexpected error occurred (${status}). Please try again.`;
}

async function request<T = any>(
  path: string,
  init?: RequestInit & { json?: any; idempotencyKey?: string }
): Promise<T> {
  const { json, headers, idempotencyKey, ...rest } = init || {};
  let hdrs = headers || {};
  if (typeof window === 'undefined') {
    try {
      const { cookies } = await import('next/headers');
      const cookie = cookies().toString();
      if (cookie) hdrs = { ...hdrs, Cookie: cookie };
    } catch {}
  }
  
  let res: Response;
  try {
    res = await fetch(pathJoin(path), {
      method: json ? "POST" : (rest.method || "GET"),
      headers: {
        Accept: "application/json",
        ...(json ? { "Content-Type": "application/json" } : {}),
        ...(idempotencyKey ? { "Idempotency-Key": idempotencyKey } : {}),
        ...hdrs,
      },
      body: json ? JSON.stringify(json) : rest.body,
      credentials: 'include',
      ...rest,
    });
  } catch (e: any) {
    // Network errors (no internet, server down, etc.)
    const networkError = new Error("Unable to connect to server. Please check your internet connection and try again.");
    (networkError as any).status = 0;
    (networkError as any).isNetworkError = true;
    throw networkError;
  }

  const text = await res.text();
  const isJSON = res.headers.get("content-type")?.includes("application/json");
  const payload: any = isJSON && text ? JSON.parse(text) : text;
  const unwrapped =
    payload && typeof payload === "object" && "data" in payload
      ? (payload as any).data
      : payload;

  if (!res.ok) {
    const serverMessage = 
      (isJSON && (unwrapped?.detail || unwrapped?.message)) ||
      (typeof unwrapped === "string" && unwrapped) ||
      res.statusText;
    
    const userFriendlyMessage = getUserFriendlyErrorMessage(res.status, path, serverMessage);
    const err: any = new Error(userFriendlyMessage);
    err.status = res.status;
    err.data = unwrapped;
    err.originalMessage = serverMessage;
    throw err;
  }
  return unwrapped as T;
}

// -------- Auth
export function getMe() {
  return request<any>('/auth/me');
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
type OrdersList = { items: any[]; total?: number };

export async function listOrders(
  q?: string,
  status?: string,
  type?: string,
  limit?: number,
  opts?: { date?: string; unassigned?: boolean }
): Promise<OrdersList> {
  const sp = new URLSearchParams();
  if (q) sp.set("q", q);
  if (status) sp.set("status", status);
  if (type) sp.set("type", type);
  if (limit) sp.set("limit", String(limit));
  if (opts?.date) sp.set("date", opts.date);
  if (opts?.unassigned) sp.set("unassigned", "true");
  const qs = sp.toString();

  const data = await request<any>(`/orders${qs ? `?${qs}` : ""}`);
  // Normalize: backend may return array or { items, total }
  if (Array.isArray(data)) return { items: data, total: data.length };
  if (data && typeof data === "object") {
    const items = Array.isArray(data.items) ? data.items : [];
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
  // Unwrap common envelope shapes: { ok, data: { parsed } }
  const payload = typeof input === "object" && "data" in input ? input.data : input;
  const parsed = payload?.parsed ? payload.parsed : payload;

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
    throw new Error("Unable to create order: Missing customer or order information. Please check the parsed data and try again.");
  }

  try {
    // Primary: top-level {customer, order}
    return await request<any>("/orders", { json: { customer, order } });
  } catch (e: any) {
    // Fallback: some backends accept { parsed: { customer, order } }
    if (e?.status === 422 || e?.status === 400) {
      try {
        return await request<any>("/orders", { json: { parsed: { customer, order } } });
      } catch (fallbackError: any) {
        // If both attempts fail, throw a user-friendly error
        throw new Error("Unable to create order. Please check that all required information is provided and try again.");
      }
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

export function markReturned(
  id: number,
  date?: string,
  opts?: {
    collect?: boolean;
    return_delivery_fee?: number;
    method?: string;
    reference?: string;
  }
) {
  const body: any = { ...(opts || {}) };
  if (date) body.date = date;
  return request<any>(`/orders/${id}/return`, {
    json: body,
    idempotencyKey: crypto.randomUUID(),
  });
}

export function markBuyback(
  id: number,
  amount: number,
  opts?: { discount?: { type: 'percent' | 'fixed'; value: number }; method?: string; reference?: string }
) {
  const body: any = { amount, ...(opts || {}) };
  return request<any>(`/orders/${id}/buyback`, {
    json: body,
    idempotencyKey: crypto.randomUUID(),
  });
}

export function cancelInstallment(
  id: number,
  payload: {
    penalty?: number;
    return_delivery_fee?: number;
    collect?: boolean;
    method?: string;
    reference?: string;
  }
) {
  return request<any>(`/orders/${id}/cancel-installment`, {
    json: payload,
    idempotencyKey: crypto.randomUUID(),
  });
}

export function orderDue(id: number, asOf?: string) {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request<any>(`/orders/${id}/due${qs}`);
}

export function markSuccess(id: number) {
  return request<any>(`/orders/${id}/success`, { method: "POST" });
}

export function updateCommission(id: number, amount: number) {
  return request<any>(`/orders/${id}/commission`, { method: "PATCH", json: { amount } });
}

// -------- Payments
export function addPayment(payload: {
  order_id: number;
  amount: number;
  date?: string;
  method?: string;
  reference?: string;
  category?: string;
  idempotencyKey?: string;
}) {
  const { idempotencyKey, ...json } = payload as any;
  return request<any>("/payments", { json, idempotencyKey });
}
export function voidPayment(paymentId: number, reason?: string) {
  return request<any>(`/payments/${paymentId}/void`, { json: { reason } });
}

export async function exportPayments(
  start: string,
  end: string,
  opts?: { mark?: boolean }
) {
  const sp = new URLSearchParams({ start, end });
  if (opts?.mark) sp.set("mark", "true");
  
  try {
    const res = await fetch(pathJoin(`/export/cash.xlsx?${sp.toString()}`), {
      credentials: "include",
    });
    
    if (!res.ok) {
      if (res.status === 404) {
        throw new Error("No payments found for the selected date range.");
      } else if (res.status === 403) {
        throw new Error("You don't have permission to export payment data. Please contact your administrator.");
      } else if (res.status >= 500) {
        throw new Error("Export service is temporarily unavailable. Please try again in a few moments.");
      } else {
        throw new Error("Unable to export payments. Please check your date range and try again.");
      }
    }
    
    return res.blob();
  } catch (e: any) {
    if (e.message) throw e; // Re-throw our custom errors
    throw new Error("Unable to connect to export service. Please check your internet connection and try again.");
  }
}

// -------- Reports
export function outstanding(type?: string, asOf?: string) {
  const sp = new URLSearchParams();
  if (type && type !== "ALL") sp.set("type", type);
  if (asOf) sp.set("as_of", asOf);
  const qs = sp.toString();
  return request<{ items: any[] }>(`/reports/outstanding${qs ? `?${qs}` : ""}`);
}

// -------- Documents
export function invoicePrintUrl(orderId: number | string) {
  return `/invoice/${orderId}/print`;
}

// -------- Drivers
export function listDrivers() {
  return request<any[]>("/drivers");
}

export function assignOrderToDriver(orderId: number | string, driverId: string) {
  return request(`/orders/${orderId}/assign`, { json: { driver_id: driverId } });
}

export function createRoute(body: { driver_id: number; secondary_driver_id?: number; route_date: string; name?: string; notes?: string }) {
  return request<any>('/routes', { json: body });
}

export function updateRoute(
  routeId: number,
  body: { driver_id?: number; secondary_driver_id?: number; route_date?: string; name?: string; notes?: string },
) {
  return request<any>(`/routes/${routeId}`, { method: 'PATCH', json: body });
}

export function listRoutes(date?: string) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return request<any[]>(`/routes${qs}`);
}

export function addOrdersToRoute(routeId: number, orderIds: number[]) {
  return request<any>(`/routes/${routeId}/orders`, { json: { order_ids: orderIds } });
}

export function createDriver(payload: {
  email: string;
  password: string;
  name?: string;
  phone?: string;
}) {
  return request<any>("/drivers", { json: payload });
}

export function listDriverCommissions(driverId: number) {
  return request<any[]>(`/drivers/${driverId}/commissions`);
}

export async function listDriverOrders(driverId: number, month?: string, limit = 500) {
  const sp = new URLSearchParams({ driver_id: String(driverId), limit: String(limit) });
  if (month) sp.set('month', month);
  const data = await request<any>(`/orders?${sp.toString()}`);
  if (Array.isArray(data)) return data;
  if (data && typeof data === 'object' && Array.isArray(data.items)) return data.items;
  return [];
}

// -------- Driver Schedule
export function getDriversWithSchedule(targetDate?: string) {
  const sp = new URLSearchParams();
  if (targetDate) sp.set('target_date', targetDate);
  return request<any>(`/driver-schedule/drivers/all${sp.toString() ? `?${sp.toString()}` : ''}`);
}

export function setDailySchedule(data: {
  driver_id: number;
  schedule_date: string;
  is_scheduled: boolean;
  shift_type?: string;
}) {
  return request<any>('/driver-schedule/daily-override', { json: data });
}

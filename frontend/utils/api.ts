// utils/api.ts
export type Json = Record<string, unknown> | unknown[];

export interface Customer {
  name: string;
  phone?: string;
  address?: string;
  [key: string]: unknown;
}

export interface Plan {
  plan_type?: string;
  months?: number;
  monthly_amount?: number;
  [key: string]: unknown;
}

export interface OrderItem {
  id?: number;
  name?: string;
  item_type?: string;
  qty?: number;
  unit_price?: number;
  monthly_amount?: number;
  line_total?: number;
  [key: string]: unknown;
}

export interface Order {
  id: number;
  code?: string;
  type?: string;
  status?: string;
  subtotal?: number;
  delivery_fee?: number;
  return_delivery_fee?: number;
  penalty_fee?: number;
  discount?: number;
  total?: number;
  paid_amount?: number;
  balance?: number;
  delivery_date?: string;
  notes?: string;
  items?: OrderItem[];
  customer?: Customer;
  plan?: Plan;
  payments?: Payment[];
  [key: string]: unknown;
}

export interface OrdersList {
  items: Order[];
  total?: number;
}

export interface ParseResponse {
  parsed?: unknown;
  [key: string]: unknown;
}

export interface Due {
  accrued?: number;
  outstanding?: number;
  [key: string]: unknown;
}

export interface Payment {
  id: number;
  date?: string;
  amount?: number;
  method?: string;
  reference?: string;
  status?: string;
  [key: string]: unknown;
}

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

async function request<T = unknown>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const { json, headers, ...rest } = init || {};
  const res = await fetch(pathJoin(path), {
    method: json ? "POST" : rest.method || "GET",
    headers: {
      Accept: "application/json",
      ...(json ? { "Content-Type": "application/json" } : {}),
      ...(headers || {}),
    },
    body: json ? JSON.stringify(json) : rest.body,
    ...rest,
  }).catch((e: unknown) => {
    const err = e as { message?: string };
    throw new Error(
      `Network error calling ${path}: ${err?.message || "failed to fetch"}`
    );
  });

  const text = await res.text();
  const isJSON = res.headers.get("content-type")?.includes("application/json");
  const data: unknown = isJSON && text ? JSON.parse(text) : text;

  if (!res.ok) {
    const parsed = data as Record<string, unknown> | string;
    const parsedRecord = parsed as Record<string, unknown>;
    const msg =
      (typeof parsed === "object" && typeof parsedRecord["detail"] === "string" && parsedRecord["detail"] as string) ||
      (typeof parsed === "object" && typeof parsedRecord["message"] === "string" && parsedRecord["message"] as string) ||
      (typeof parsed === "string" && parsed) ||
      res.statusText;
    const err = new Error(msg || `HTTP ${res.status}`) as Error & {
      status?: number;
      data?: unknown;
    };
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
export function parseMessage(text: string): Promise<ParseResponse> {
  return request<ParseResponse>("/parse", { json: { text, message: text } });
}

// -------- Orders (normalized)

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

  const data = await request<unknown>(`/orders${qs ? `?${qs}` : ""}`);
  // Normalize: backend may return array or { items, total }
  if (Array.isArray(data)) return { items: data as Order[], total: data.length };
  if (data && typeof data === "object") {
    const obj = data as { items?: unknown; total?: unknown };
    const items = Array.isArray(obj.items) ? (obj.items as Order[]) : [];
    const total =
      typeof obj.total === "number"
        ? obj.total
        : Array.isArray(obj.items)
        ? obj.items.length
        : undefined;
    return { items, total };
  }
  return { items: [], total: 0 };
}

export function getOrder(id: number | string): Promise<Order> {
  return request<Order>(`/orders/${id}`);
}

// Optional: tweak parsed payload before posting if your parser is loose
function normalizeParsedForOrder(input: unknown): unknown {
  if (!input) return input;
  const obj = input as { parsed?: unknown };
  const parsed = obj.parsed ?? input;

  if (typeof parsed === "object" && parsed !== null && "order" in parsed) {
    const order = (parsed as { order?: Record<string, unknown> }).order;
    if (
      order &&
      !(order.code as unknown) &&
      Array.isArray(order.items) &&
      order.items.length
    ) {
      const guess = (order.items as Record<string, unknown>[]).find(
        (it) => typeof it.sku === "string"
      );
      if (
        guess &&
        typeof guess.sku === "string" &&
        /^[A-Za-z]{1,3}\d{3,5}$/.test(guess.sku)
      ) {
        order.code = guess.sku as string;
        (guess as Record<string, unknown>).sku = null;
      }
    }
  }
  return parsed;
}

export async function createOrderFromParsed(parsed: unknown): Promise<Order> {
  const normalized = normalizeParsedForOrder(parsed) as {
    parsed?: unknown;
    customer?: Customer;
    order?: Record<string, unknown>;
  };
  const payload = normalized.parsed
    ? (normalized.parsed as Record<string, unknown>)
    : normalized;

  const customer = (payload as { customer?: Customer }).customer;
  const order = (payload as { order?: Record<string, unknown> }).order;

  if (!customer || !order) {
    throw new Error(
      "Parsed payload missing {customer, order}. Please re-parse or edit JSON."
    );
  }

  try {
    return await request<Order>("/orders", { json: { customer, order } });
  } catch (e: unknown) {
    const err = e as { status?: number };
    if (err?.status === 422 || err?.status === 400) {
      return request<Order>("/orders", { json: { parsed: { customer, order } } });
    }
    throw e;
  }
}

export function createManualOrder(payload: {
  customer: Customer;
  order: Record<string, unknown>;
}): Promise<Order> {
  return request<Order>("/orders", { json: payload });
}

export function updateOrder(
  id: number,
  patch: Record<string, unknown>
): Promise<Order> {
  return request<Order>(`/orders/${id}`, { method: "PATCH", json: patch }).catch(
    (e: unknown) => {
      const err = e as { status?: number };
      if (err?.status === 405)
        return request<Order>(`/orders/${id}`, { method: "PUT", json: patch });
      throw e;
    }
  );
}

export async function voidOrder(
  id: number,
  reason?: string
): Promise<Order> {
  try {
    return await request<Order>(`/orders/${id}/void`, { json: { reason } });
  } catch (e1: unknown) {
    const err1 = e1 as { status?: number };
    if (err1?.status === 404 || err1?.status === 405) {
      try {
        return await request<Order>(`/orders/${id}/cancel`, { json: { reason } });
      } catch (e2: unknown) {
        const err2 = e2 as { status?: number };
        if (err2?.status === 404 || err2?.status === 405)
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

export function markReturned(
  id: number,
  date?: string
): Promise<Order | { order: Order }> {
  const body: Record<string, unknown> = {};
  if (date) body.date = date;
  return request<Order | { order: Order }>(`/orders/${id}/return`, { json: body });
}

export function markBuyback(
  id: number,
  amount: number
): Promise<Order | { order: Order }> {
  return request<Order | { order: Order }>(`/orders/${id}/buyback`, {
    json: { amount },
  });
}

export function orderDue(id: number, asOf?: string): Promise<Due> {
  const qs = asOf ? `?as_of=${encodeURIComponent(asOf)}` : "";
  return request<Due>(`/orders/${id}/due${qs}`);
}

// -------- Payments
export function addPayment(payload: {
  order_id: number;
  amount: number;
  date?: string;
  method?: string;
  reference?: string;
  category?: string;
}): Promise<Payment> {
  return request<Payment>("/payments", { json: payload });
}
export function voidPayment(paymentId: number, reason?: string): Promise<Payment> {
  return request<Payment>(`/payments/${paymentId}/void`, { json: { reason } });
}

// -------- Reports
export function outstanding(type?: "INSTALLMENT" | "RENTAL") {
  const qs = type ? `?type=${encodeURIComponent(type)}` : "";
  return request<{ items: Order[] }>(`/reports/outstanding${qs}`);
}

// -------- Documents
export function invoicePdfUrl(orderId: number) {
  const base = API_BASE;
  return `${base}/documents/invoice/${orderId}.pdf`;
}


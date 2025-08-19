export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Json = Record<string, any>;

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(init && init.headers ? init.headers : {}),
    },
    ...init,
    // Include credentials only if your backend uses cookies; otherwise omit
  });
  const text = await res.text();
  let data: any = undefined;
  try { data = text ? JSON.parse(text) : null; } catch { data = text; }

  if (!res.ok) {
    const message = (data && (data.detail || data.message)) || res.statusText;
    throw new Error(typeof message === "string" ? message : JSON.stringify(message));
  }
  return data as T;
}

// Health
export function ping() { return request<{ ok: boolean } | string>("/healthz"); }

// Parse
export function parseMessage(text: string) {
  // send both keys to be compatible with either backend
  return request<Json>("/parse", { method: "POST", body: JSON.stringify({ text, message: text }) });
}

// Orders
export function listOrders() { return request<Json[]>("/orders"); }
export function getOrder(id: string | number) { return request<Json>(`/orders/${id}`); }
export function createOrderFromParsed(parsed: Json) { 
  // Some backends expect { parsed } wrapper; try direct first, fallback handled in UI.
  return request<Json>("/orders", { method: "POST", body: JSON.stringify(parsed) });
}
export function updateOrder(id: number, patch: Json) {
  return request<Json>(`/orders/${id}`, { method: "PATCH", body: JSON.stringify(patch) });
}
export function voidOrder(id: number, reason?: string) {
  // Prefer dedicated endpoint; fallback to PATCH status
  return request<Json>(`/orders/${id}/void`, { method: "POST", body: JSON.stringify({ reason }) });
}

// Payments
export function addPayment(payload: { order_id: number; amount: number; date?: string; method?: string; reference?: string; category?: string; }) {
  return request<Json>("/payments", { method: "POST", body: JSON.stringify(payload) });
}
export function voidPayment(paymentId: number, reason?: string) {
  return request<Json>(`/payments/${paymentId}/void`, { method: "POST", body: JSON.stringify({ reason }) });
}

// Reports
export function outstanding(type: "INSTALLMENT" | "RENTAL") {
  return request<Json[]>(`/reports/outstanding?type=${encodeURIComponent(type)}`);
}

// Documents
export function invoicePdfUrl(orderId: number) {
  return `${API_URL}/documents/invoice/${orderId}.pdf`;
}

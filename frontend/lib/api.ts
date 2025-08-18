export const API_BASE = process.env.NEXT_PUBLIC_API_BASE || "http://localhost:8000";

export async function api<T=any>(path: string, opts: RequestInit = {}): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...(opts.headers||{}) },
    ...opts
  });
  if (!res.ok) {
    const txt = await res.text().catch(()=> "");
    throw new Error(txt || `HTTP ${res.status}`);
  }
  return res.json();
}

export async function getOutstanding(type?: string) {
  const q = type ? `?type=${encodeURIComponent(type)}` : "";
  const res = await fetch(`${API_BASE}/reports/outstanding${q}`);
  if (!res.ok) throw new Error("Failed to load outstanding");
  return res.json();
}

export async function updateOrder(orderId: number, body: any) {
  const res = await fetch(`${API_BASE}/orders/${orderId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Failed to update order");
  return res.json();
}

export async function voidOrder(orderId: number, reason?: string) {
  const res = await fetch(`${API_BASE}/orders/${orderId}/void`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to void order");
  return res.json();
}

export async function voidPayment(paymentId: number, reason?: string) {
  const res = await fetch(`${API_BASE}/payments/${paymentId}/void`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason }),
  });
  if (!res.ok) throw new Error("Failed to void payment");
  return res.json();
}

export async function createOrder(payload: any) {
  const res = await fetch(`${API_BASE}/orders`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Create failed");
  return res.json();
}

export async function getOrders() {
  const res = await fetch(`${API_BASE}/orders`);
  if (!res.ok) throw new Error("Failed to load orders");
  return res.json();
}

export async function addPayment(payload: any) {
  const res = await fetch(`${API_BASE}/payments`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Payment failed");
  return res.json();
}

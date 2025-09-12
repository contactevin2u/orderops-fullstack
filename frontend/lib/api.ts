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
// Advanced parsing pipeline
export function parseAdvancedMessage(text: string) {
  return request<any>("/parse/advanced", { json: { text, message: text } });
}

// Simple quotation parser
export function parseQuotationMessage(text: string) {
  return request<any>("/parse/quotation", { json: { text, message: text } });
}

// Individual stages for testing/debugging
export function classifyMessage(text: string) {
  return request<any>("/parse/classify", { json: { text, message: text } });
}

export function findMotherOrder(text: string) {
  return request<any>("/parse/find-order", { json: { text, message: text } });
}

// Background job processing
export function createParseJob(text: string, sessionId?: string) {
  return request<any>("/jobs/parse", { 
    json: { text, session_id: sessionId } 
  });
}

export function getJobStatus(jobId: string) {
  return request<any>(`/jobs/${jobId}`);
}

export function listJobs(sessionId?: string, limit = 20) {
  const sp = new URLSearchParams();
  if (sessionId) sp.set("session_id", sessionId);
  sp.set("limit", String(limit));
  return request<any>(`/jobs?${sp.toString()}`);
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
export function normalizeParsedForOrder(input: any) {
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
  const sp = new URLSearchParams();
  sp.set("order_id", String(id));
  sp.set("include_zero_balance", "true");
  if (asOf) sp.set("as_of", asOf);
  return request<any>(`/reports/outstanding?${sp.toString()}`).then(r => {
    // Return single order data in same format as old API
    const item = r.items?.[0];
    return item || { balance: 0, expected: 0, paid: 0, to_collect: 0, to_refund: 0, accrued: 0 };
  });
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
  return request<any>(`/routes/${routeId}/orders`, { method: 'POST', json: { order_ids: orderIds } });
}

export function getRouteOrders(routeId: number) {
  return request<any[]>(`/routes/${routeId}/orders`);
}

export function createDriver(payload: {
  email: string;
  password: string;
  name?: string;
  phone?: string;
  base_warehouse?: string;
}) {
  return request<any>("/drivers", { json: payload });
}

export function fetchDriver(driverId: number) {
  return request<any>(`/drivers/${driverId}`);
}

export function updateDriver(driverId: number, payload: {
  name?: string;
  phone?: string;
  base_warehouse?: string;
}) {
  return request<any>(`/drivers/${driverId}`, { 
    method: "PUT",
    json: payload 
  });
}

export function listDriverCommissions(driverId: number) {
  return request<any[]>(`/drivers/${driverId}/commissions`);
}

export function listUpsellRecords(params?: { 
  limit?: number; 
  offset?: number; 
  driver_id?: number; 
  status?: string; 
}) {
  const sp = new URLSearchParams();
  if (params?.limit) sp.set('limit', String(params.limit));
  if (params?.offset) sp.set('offset', String(params.offset));
  if (params?.driver_id) sp.set('driver_id', String(params.driver_id));
  if (params?.status) sp.set('status', params.status);
  
  return request<any>(`/upsells?${sp.toString()}`);
}

export function releaseUpsellIncentive(upsellId: number) {
  return request<any>(`/upsells/${upsellId}/release`, { method: 'POST' });
}

export function getUpsellSummary(params?: { start_date?: string; end_date?: string }) {
  const sp = new URLSearchParams();
  if (params?.start_date) sp.set('start_date', params.start_date);
  if (params?.end_date) sp.set('end_date', params.end_date);
  
  return request<any>(`/upsells/summary?${sp.toString()}`);
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

// -------- UID Inventory
export function getInventoryConfig() {
  return request<{
    uid_inventory_enabled: boolean;
    uid_scan_required_after_pod: boolean;
    inventory_mode: string;
  }>('/inventory/config');
}


export function getLorryStock(driverId: number, date: string) {
  const qs = `?date=${encodeURIComponent(date)}`;
  return request<{
    date: string;
    driver_id: number;
    items: Array<{
      sku_id: number;
      sku_name: string;
      expected_count: number;
      scanned_count?: number;
      variance?: number;
    }>;
    total_expected: number;
    total_scanned?: number;
    total_variance?: number;
  }>(`/inventory/lorry/${driverId}/stock${qs}`);
}

export function uploadLorryStock(
  driverId: number,
  data: {
    as_of_date: string;
    lines: Array<{ sku_id: number; qty_counted: number }>;
  }
) {
  return request<{
    success: boolean;
    message: string;
    reconciliation?: {
      as_of_date: string;
      driver_id: number;
      skus: Array<{
        sku_id: number;
        sku_code: string;
        yesterday_count: number;
        issued_yesterday: number;
        returned_yesterday: number;
        expected_today: number;
        counted_today: number;
        variance: number;
      }>;
      total_variance: number;
    };
    items_processed: number;
  }>(`/inventory/lorry/${driverId}/stock/upload`, { json: data });
}

export function resolveSKU(name: string, threshold = 0.8) {
  return request<{
    matches: Array<{
      sku_id: number;
      sku_name: string;
      confidence: number;
      match_type: 'exact' | 'alias' | 'fuzzy';
    }>;
    suggestions: string[];
  }>('/inventory/sku/resolve', { json: { name, threshold } });
}

export function addSKUAlias(skuId: number, alias: string) {
  return request<{
    success: boolean;
    message: string;
    alias_id: number;
  }>('/inventory/sku/alias', { json: { sku_id: skuId, alias } });
}

export function getOrderUIDs(orderId: number | string) {
  return request<{
    order_id: number;
    uids: Array<{
      id: number;
      uid: string;
      action: 'ISSUE' | 'RETURN';
      sku_id?: number;
      sku_name?: string;
      scanned_at: string;
      driver_name?: string;
      notes?: string;
    }>;
    total_issued: number;
    total_returned: number;
  }>(`/orders/${orderId}/uids`);
}

// -------- UID Generation and Management
export function generateUID(data: {
  sku_id: number;
  item_type: 'NEW' | 'RENTAL';
  serial_number?: string;
}) {
  return request<{
    success: boolean;
    items: Array<{
      uid: string;
      type: string;
      copy_number?: number;
      serial?: string;
    }>;
    message: string;
  }>('/inventory/generate-uid', { json: data });
}

export function scanUID(data: {
  order_id: number;
  action: 'ISSUE' | 'RETURN' | 'LOAD_OUT' | 'DELIVER' | 'REPAIR' | 'SWAP' | 'LOAD_IN';
  uid: string;
  sku_id?: number;
  notes?: string;
}) {
  return request<{
    success: boolean;
    message: string;
    uid: string;
    action: string;
    sku_name?: string;
    order_item_id?: number;
  }>('/inventory/uid/scan', { json: data });
}

export function getDriverStockStatus(driverId: number, date?: string) {
  const qs = date ? `?date=${encodeURIComponent(date)}` : '';
  return request<{
    driver_id: number;
    stock_items: Array<{
      sku_name: string;
      count: number;
      items: Array<{
        uid: string;
        serial?: string;
        type: string;
        copy_number?: number;
      }>;
    }>;
    total_items: number;
  }>(`/inventory/admin/drivers/${driverId}/stock-status${qs}`);
}

// -------- UID Ledger
export function getUIDLedgerHistory(uid: string) {
  return request<{
    uid: string;
    total_entries: number;
    history: Array<{
      id: number;
      uid: string;
      action: string;
      scanned_at: string;
      scanner: {
        type: 'admin' | 'driver' | 'manual';
        id?: number;
        name: string;
      };
      source: string;
      order_id?: number;
      order_reference?: string;
      customer_name?: string;
      lorry_id?: string;
      location_notes?: string;
      notes?: string;
      recorded_at: string;
    }>;
  }>(`/inventory/uid/${uid}/ledger`);
}

export function getLedgerAuditTrail(params: {
  start_date?: string;
  end_date?: string;
  uid?: string;
  action?: string;
  scanner_id?: number;
  order_id?: number;
  limit?: number;
} = {}) {
  const searchParams = new URLSearchParams();
  Object.entries(params).forEach(([key, value]) => {
    if (value !== undefined && value !== null) {
      searchParams.append(key, value.toString());
    }
  });
  
  const queryString = searchParams.toString();
  return request<{
    total_entries: number;
    entries: Array<{
      id: number;
      uid: string;
      action: string;
      scanned_at: string;
      scanner: {
        type: 'admin' | 'driver' | 'manual';
        id?: number;
        name: string;
      };
      source: string;
      order_id?: number;
      order_reference?: string;
      customer_name?: string;
      location: {
        lorry_id?: string;
        notes?: string;
      };
      notes?: string;
      item_info?: {
        uid: string;
        sku_id?: number;
        sku_name?: string;
        item_type: string;
        status: string;
        oem_serial?: string;
      };
      recorded_at: string;
    }>;
    summary: {
      actions: Record<string, number>;
      date_range: {
        start?: string;
        end?: string;
      };
    };
  }>(`/inventory/ledger/audit-trail${queryString ? `?${queryString}` : ''}`);
}

export function getLedgerStatistics(days: number = 30) {
  return request<{
    period_days: number;
    total_scans: number;
    scans_by_action: Record<string, number>;
    scans_by_source: Record<string, number>;
  }>(`/inventory/ledger/statistics?days=${days}`);
}

export function recordUIDScan(uid: string, data: {
  action: string;
  order_id?: number;
  sku_id?: number;
  source?: string;
  lorry_id?: string;
  location_notes?: string;
  notes?: string;
  customer_name?: string;
  order_reference?: string;
}) {
  return request<{
    success: boolean;
    message: string;
    entry_id: number;
    uid: string;
    action: string;
    recorded_at: string;
  }>(`/inventory/uid/${uid}/scan`, { json: data });
}

// -------- SKU Management
export function getAllSKUs() {
  return request<Array<{
    id: number;
    code: string;
    name: string;
    category?: string;
    description?: string;
    price: number;
    is_serialized: boolean;
    is_active: boolean;
    created_at: string;
  }>>('/skus');
}

export function createSKU(data: {
  code: string;
  name: string;
  category?: string;
  description?: string;
  price: number;
  is_serialized?: boolean;
}) {
  return request<{
    success: boolean;
    sku_id: number;
    message: string;
  }>('/skus', { json: data });
}

export function updateSKU(skuId: number, data: {
  code?: string;
  name?: string;
  category?: string;
  description?: string;
  price?: number;
  is_serialized?: boolean;
  is_active?: boolean;
}) {
  return request<{
    success: boolean;
    message: string;
  }>(`/skus/${skuId}`, { method: 'PUT', json: data });
}

export function deleteSKU(skuId: number) {
  return request<{
    success: boolean;
    message: string;
  }>(`/skus/${skuId}`, { method: 'DELETE' });
}

// -------- QR Code Generation
export function generateQRCode(data: {
  uid?: string;
  order_id?: number;
  content?: string;
  size?: number;
}) {
  return request<{
    success: boolean;
    qr_code_base64: string;
    format: string;
    message: string;
  }>('/inventory/generate-qr', { json: data });
}

// -------- Commission Release Management
export function analyzeCommissionEligibility(tripId: number) {
  return request<{
    trip_id: number;
    trip_status: string;
    ai_verification: {
      payment_method: string;
      confidence_score: number;
      cash_collection_required: boolean;
      analysis_details: string;
      timestamp: string;
    };
    existing_commissions: number;
    commission_entries: Array<{
      id: number;
      driver_id: number;
      amount: number;
      driver_role: string;
      status: string;
    }>;
  }>(`/commission-release/analyze/${tripId}`, { method: 'POST' });
}

export function releaseCommission(data: {
  trip_id: number;
  manual_override?: boolean;
  cash_collected?: boolean;
  notes?: string;
}) {
  return request<{
    success: boolean;
    trip_id: number;
    payment_method: string;
    cash_collection_required: boolean;
    commission_released: boolean;
    released_entries: number;
    ai_verification: any;
    message: string;
  }>('/commission-release/release', { json: data });
}

export function getPendingCommissions() {
  return request<{
    pending_commissions: Array<{
      trip_id: number;
      order_id: number;
      order_code: string;
      customer_name: string;
      total_amount: number;
      delivered_at: string | null;
      primary_driver_id: number;
      secondary_driver_id: number | null;
      pending_commission_entries: number;
      has_pod_photos: boolean;
      pod_photo_count: number;
    }>;
    total_count: number;
  }>('/commission-release/pending');
}

export function markCashCollected(tripId: number, notes?: string) {
  return request<{
    success: boolean;
    trip_id: number;
    message: string;
  }>(`/commission-release/mark-cash-collected/${tripId}`, { 
    method: 'POST',
    json: { notes: notes || '' }
  });
}

export type Json = Record<string, any> | any[];

function normalizeBase(s?: string) {
  if (!s) return "";
  return s.replace(/\/+$/, "");
}

const ENV_BASE = normalizeBase(process.env.NEXT_PUBLIC_API_URL);
const API_BASE = ENV_BASE || "/_api";

function pathJoin(p: string) { return `${API_BASE}${p.startsWith("/")?p:`/${p}`}`; }

async function request<T=any>(path: string, init?: RequestInit & { json?: any }): Promise<T> {
  const { json, headers, ...rest } = init || {};
  const res = await fetch(pathJoin(path), {
    method: json ? "POST" : (rest.method || "GET"),
    headers: {
      Accept: "application/json",
      ...(json ? {"Content-Type":"application/json"} : {}),
      ...(headers||{}),
    },
    body: json ? JSON.stringify(json) : rest.body,
    ...rest,
  }).catch((e:any)=>{
    throw new Error(`Network error calling ${path}: ${e?.message || "failed to fetch"}`);
  });

  const text = await res.text();
  const isJSON = res.headers.get("content-type")?.includes("application/json");
  const data: any = isJSON && text ? JSON.parse(text) : text;

  if (!res.ok) {
    const msg = (isJSON && (data?.detail || data?.message)) || (typeof data==="string" && data) || res.statusText;
    const err:any = new Error(msg || `HTTP ${res.status}`);
    err.status = res.status; err.data = data;
    throw err;
  }
  return data as T;
}

// health
export function ping(){ return request<{ok:boolean} | string>("/healthz"); }

// parse
export function parseMessage(text: string){ return request<Json>("/parse", { json: { text, message: text } }); }

// orders
export function listOrders(q?: string, status?: string, type?: string){
  const sp = new URLSearchParams();
  if(q) sp.set("q", q);
  if(status) sp.set("status", status);
  if(type) sp.set("type", type);
  const qs = sp.toString();
  return request<{ items: any[], total?: number }>(`/orders${qs?`?${qs}`:""}`);
}
export function getOrder(id: number | string){ return request<any>(`/orders/${id}`); }
export async function createOrderFromParsed(parsed: Json){
  try { return await request<any>("/orders", { json: parsed }); }
  catch(e:any){ if(e?.status===400 || e?.status===422) return await request<any>("/orders", { json: { parsed } }); throw e; }
}
export function updateOrder(id:number, patch:any){
  return request<any>(`/orders/${id}`, { method:"PATCH", json: patch }).catch((e:any)=>{
    if(e?.status===405) return request<any>(`/orders/${id}`, { method:"PUT", json: patch });
    throw e;
  });
}
export async function voidOrder(id:number, reason?:string){
  try { return await request<any>(`/orders/${id}/void`, { json: { reason } }); }
  catch(e1:any){
    if(e1?.status===404 || e1?.status===405){
      try { return await request<any>(`/orders/${id}/cancel`, { json: { reason } }); }
      catch(e2:any){
        if(e2?.status===404 || e2?.status===405) return await updateOrder(id, { status:"CANCELLED", cancel_reason: reason||"" });
        throw e2;
      }
    }
    throw e1;
  }
}
export function markReturned(id:number, date?:string){ return request<any>(`/orders/${id}/return`, { json: { date } }); }
export function markBuyback(id:number, amount:number){ return request<any>(`/orders/${id}/buyback`, { json: { amount } }); }

// payments
export function addPayment(payload:{order_id:number; amount:number; date?:string; method?:string; reference?:string; category?:string;}){
  return request<any>("/payments", { json: payload });
}
export function voidPayment(paymentId:number, reason?:string){
  return request<any>(`/payments/${paymentId}/void`, { json: { reason } });
}

// reports
export function outstanding(type?: "INSTALLMENT" | "RENTAL"){
  const qs = type?`?type=${encodeURIComponent(type)}`:"";
  return request<{items:any[]}>(`/reports/outstanding${qs}`);
}

// documents
export function invoicePdfUrl(orderId:number){
  const base = API_BASE;
  return `${base}/documents/invoice/${orderId}.pdf`;
}

import { useState } from "react";
import { updateOrder, createOrderFromParsed } from "@/utils/api";

type Json = Record<string, any>;

export default function OrderForm({ parsed, orderId, onSaved }:{ parsed?: Json; orderId?: number; onSaved: (o: any)=>void }) {
  const [data, setData] = useState<Json>(parsed || {});
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function set(path: string, value: any) {
    setData(prev => {
      const next = structuredClone(prev || {});
      const parts = path.split(".");
      let cur: any = next;
      for (let i = 0; i < parts.length - 1; i++) {
        const k = parts[i];
        cur[k] = cur[k] ?? {};
        cur = cur[k];
      }
      cur[parts[parts.length - 1]] = value;
      return next;
    });
  }

  async function save() {
    setSaving(true); setError(null);
    try {
      if (orderId) {
        const patch = data.order || data; // support editing
        const out = await updateOrder(orderId, patch);
        onSaved(out);
      } else {
        // Attempt direct POST first; if backend expects {parsed}, catch & retry
        try {
          const out = await createOrderFromParsed(data);
          onSaved(out);
        } catch (e: any) {
          const out = await createOrderFromParsed({ parsed: data });
          onSaved(out);
        }
      }
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h3 style={{marginTop:0}}>{orderId ? "Edit Order" : "Create Order"}</h3>
      <div className="row">
        <div className="col">
          <label>Order Code</label>
          <input className="input" value={data?.order?.code || ""} onChange={e=>set("order.code", e.target.value)} placeholder="e.g. KP2017"/>
        </div>
        <div className="col">
          <label>Type</label>
          <select className="input" value={data?.order?.type || ""} onChange={e=>set("order.type", e.target.value)}>
            <option value="">Select</option>
            <option value="OUTRIGHT">OUTRIGHT</option>
            <option value="INSTALLMENT">INSTALLMENT</option>
            <option value="RENTAL">RENTAL</option>
          </select>
        </div>
        <div className="col">
          <label>Delivery Date</label>
          <input className="input" value={data?.order?.delivery_date || ""} onChange={e=>set("order.delivery_date", e.target.value)} placeholder="YYYY-MM-DD or DD/MM"/>
        </div>
      </div>

      <div className="row" style={{marginTop:8}}>
        <div className="col">
          <label>Customer Name</label>
          <input className="input" value={data?.customer?.name || ""} onChange={e=>set("customer.name", e.target.value)} />
        </div>
        <div className="col">
          <label>Phone</label>
          <input className="input" value={data?.customer?.phone || ""} onChange={e=>set("customer.phone", e.target.value)} />
        </div>
      </div>
      <div style={{marginTop:8}}>
        <label>Address</label>
        <textarea className="input" value={data?.customer?.address || ""} onChange={e=>set("customer.address", e.target.value)} />
      </div>

      <div className="row" style={{marginTop:8}}>
        <div className="col"><label>Delivery Fee</label><input className="input" type="number" value={data?.order?.charges?.delivery_fee ?? 0} onChange={e=>set("order.charges.delivery_fee", Number(e.target.value))}/></div>
        <div className="col"><label>Return Delivery Fee</label><input className="input" type="number" value={data?.order?.charges?.return_delivery_fee ?? 0} onChange={e=>set("order.charges.return_delivery_fee", Number(e.target.value))}/></div>
        <div className="col"><label>Penalty Fee</label><input className="input" type="number" value={data?.order?.charges?.penalty_fee ?? 0} onChange={e=>set("order.charges.penalty_fee", Number(e.target.value))}/></div>
        <div className="col"><label>Discount</label><input className="input" type="number" value={data?.order?.charges?.discount ?? 0} onChange={e=>set("order.charges.discount", Number(e.target.value))}/></div>
      </div>

      <details style={{marginTop:8}}>
        <summary>Plan (optional)</summary>
        <div className="row" style={{marginTop:8}}>
          <div className="col"><label>Plan Type</label>
            <select className="input" value={data?.order?.plan?.plan_type || ""} onChange={e=>set("order.plan.plan_type", e.target.value)}>
              <option value="">Select</option>
              <option value="INSTALLMENT">INSTALLMENT</option>
              <option value="RENTAL">RENTAL</option>
            </select>
          </div>
          <div className="col"><label>Start Date</label><input className="input" placeholder="YYYY-MM-DD" value={data?.order?.plan?.start_date || ""} onChange={e=>set("order.plan.start_date", e.target.value)}/></div>
          <div className="col"><label>Months</label><input className="input" type="number" value={data?.order?.plan?.months ?? ""} onChange={e=>set("order.plan.months", Number(e.target.value))}/></div>
          <div className="col"><label>Monthly Amount</label><input className="input" type="number" value={data?.order?.plan?.monthly_amount ?? ""} onChange={e=>set("order.plan.monthly_amount", Number(e.target.value))}/></div>
        </div>
      </details>

      <div className="row" style={{marginTop:12, alignItems:'center'}}>
        <div className="col">
          <button className="btn" onClick={save} disabled={saving}>{saving ? "Saving..." : (orderId ? "Save Changes" : "Create Order")}</button>
        </div>
        <div className="col">{error && <span style={{color:"var(--err)"}}>{error}</span>}</div>
      </div>

      <details style={{marginTop:12}}>
        <summary>Raw JSON</summary>
        <pre className="code">{JSON.stringify(data, null, 2)}</pre>
      </details>
    </div>
  );
}

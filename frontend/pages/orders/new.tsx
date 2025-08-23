import Layout from "@/components/Layout";
import React from "react";
import { useRouter } from "next/router";
import { createManualOrder, parseMessage } from "@/utils/api";

export default function NewOrderPage(){
  const router = useRouter();
  const [custName,setCustName] = React.useState("");
  const [custPhone,setCustPhone] = React.useState("");
  const [custAddress,setCustAddress] = React.useState("");

  const [type,setType] = React.useState("OUTRIGHT");
  const [orderCode,setOrderCode] = React.useState("");
  const [deliveryDate,setDeliveryDate] = React.useState("");
  const [notes,setNotes] = React.useState("");

  const [items,setItems] = React.useState<any[]>([{ name:"", item_type:"OUTRIGHT", qty:1, unit_price:"", monthly_amount:"" }]);

  const [deliveryFee,setDeliveryFee] = React.useState("");
  const [returnDeliveryFee,setReturnDeliveryFee] = React.useState("");

  const [planType,setPlanType] = React.useState("");
  const [planMonths,setPlanMonths] = React.useState("");
  const [planMonthly,setPlanMonthly] = React.useState("");

  const [busy,setBusy] = React.useState(false);
  const [err,setErr] = React.useState("");
  const [rawText, setRawText] = React.useState("");

  // Reuse helper from parse page to be tolerant of slightly different shapes
  function normalizeParsedForOrder(input: any) {
    if (!input) return null;
    const payload = typeof input === "object" && "parsed" in input ? input.parsed : input;
    const core = payload && payload.data ? payload.data : payload;
    if (core?.customer && core?.order) return { customer: core.customer, order: core.order };
    if (!core) return null;
    if (!core.customer && (core.order || core.items)) {
      return { customer: core.customer || {}, order: core.order || core };
    }
    return core;
  }

  function updateItem(idx:number, field:string, value:any){
    const copy = [...items];
    copy[idx] = { ...copy[idx], [field]: value };
    setItems(copy);
  }

  function addItem(){
    setItems([...items, { name:"", item_type:"OUTRIGHT", qty:1, unit_price:"", monthly_amount:"" }]);
  }

  function removeItem(idx:number){
    setItems(items.filter((_,i)=>i!==idx));
  }

  async function onParse(){
    setBusy(true); setErr("");
    try {
      const res = await parseMessage(rawText);
      const parsed = normalizeParsedForOrder(res) || {};
      const customer = parsed.customer || {};
      const order = parsed.order || {};

      const steps: Array<() => void> = [
        () => setCustName(customer.name || ""),
        () => setCustPhone(customer.phone || ""),
        () => setCustAddress(customer.address || ""),
        () => setType(order.type || "OUTRIGHT"),
        () => setOrderCode(order.code || ""),
        () => setDeliveryDate((order.delivery_date || "").split("T")[0] || ""),
        () => setNotes(order.notes || ""),
        () => setDeliveryFee(String(order?.charges?.delivery_fee ?? "")),
        () => setReturnDeliveryFee(String(order?.charges?.return_delivery_fee ?? "")),
        () => {
          const pl = order.plan || {};
          setPlanType(pl.plan_type || "");
          setPlanMonths(pl.months ? String(pl.months) : "");
          setPlanMonthly(pl.monthly_amount ? String(pl.monthly_amount) : "");
        },
        () => {
          if (Array.isArray(order.items) && order.items.length) {
            setItems(order.items.map((it: any) => ({
              name: it.name || "",
              item_type: it.item_type || "OUTRIGHT",
              qty: String(it.qty ?? 1),
              unit_price: String(it.unit_price ?? ""),
              monthly_amount: String(it.monthly_amount ?? ""),
            })));
          }
        },
      ];
      steps.forEach((fn, idx) => setTimeout(fn, idx * 150));
    } catch (e: any) {
      setErr(e?.message || "Parse failed");
    } finally {
      setBusy(false);
    }
  }

  async function onCreate(){
    setBusy(true); setErr("");
    try{
      const payload = {
        customer: { name: custName, phone: custPhone || undefined, address: custAddress || undefined },
        order: {
          code: orderCode || undefined,
          type,
          delivery_date: deliveryDate || undefined,
          notes: notes || undefined,
          items: items.map(it=>({
            name: it.name,
            item_type: it.item_type,
            qty: Number(it.qty||0),
            unit_price: Number(it.unit_price||0),
            line_total: Number(it.unit_price||0) * Number(it.qty||0),
            ...(it.monthly_amount ? { monthly_amount: Number(it.monthly_amount||0) } : {})
          })),
          charges: {
            delivery_fee: Number(deliveryFee||0),
            return_delivery_fee: Number(returnDeliveryFee||0)
          },
          ...(planType || planMonths || planMonthly ? {
            plan: {
              plan_type: planType || undefined,
              months: planMonths ? Number(planMonths) : undefined,
              monthly_amount: planMonthly ? Number(planMonthly) : undefined
            }
          } : {})
        }
      };
      const out = await createManualOrder(payload);
      const oid = out?.id || out?.order_id;
      if(oid) router.push(`/orders/${oid}`);
    }catch(e:any){ setErr(e?.message || "Create failed"); }
    finally{ setBusy(false); }
  }

  return (
    <Layout>
      <div className="card">
        <h2 style={{marginTop:0}}>New Order</h2>
        <div style={{marginBottom:12}}>
          <label>Paste Message to Parse</label>
          <textarea
            className="textarea"
            rows={4}
            placeholder="Paste message here..."
            value={rawText}
            onChange={e=>setRawText(e.target.value)}
          />
          <button className="btn secondary" onClick={onParse} disabled={busy || !rawText.trim()} style={{marginTop:8}}>Parse</button>
        </div>
        <div className="row">
          <div className="col"><label>Customer Name</label><input className="input" value={custName} onChange={e=>setCustName(e.target.value)} /></div>
          <div className="col"><label>Phone</label><input className="input" value={custPhone} onChange={e=>setCustPhone(e.target.value)} /></div>
        </div>
        <div style={{marginTop:8}}><label>Address</label><textarea className="textarea" rows={2} value={custAddress} onChange={e=>setCustAddress(e.target.value)} /></div>
        <div className="row">
          <div className="col"><label>Type</label>
            <select className="select" value={type} onChange={e=>setType(e.target.value)}>
              <option>OUTRIGHT</option>
              <option>INSTALLMENT</option>
              <option>RENTAL</option>
              <option>MIXED</option>
            </select>
          </div>
          <div className="col"><label>Order Code</label><input className="input" value={orderCode} onChange={e=>setOrderCode(e.target.value)} /></div>
          <div className="col"><label>Delivery Date</label><input className="input" type="date" value={deliveryDate} onChange={e=>setDeliveryDate(e.target.value)} /></div>
        </div>
        <div style={{marginTop:8}}><label>Notes</label><textarea className="textarea" rows={2} value={notes} onChange={e=>setNotes(e.target.value)} /></div>

        <div className="hr" />
        <h3>Items</h3>
        <table className="table">
          <thead><tr><th>Name</th><th>Type</th><th>Qty</th><th>Unit Price</th><th>Monthly</th><th></th></tr></thead>
          <tbody>
            {items.map((it,idx)=>(
              <tr key={idx}>
                <td><input className="input" value={it.name} onChange={e=>updateItem(idx,'name',e.target.value)} /></td>
                <td>
                  <select className="select" value={it.item_type} onChange={e=>updateItem(idx,'item_type',e.target.value)}>
                    <option>OUTRIGHT</option>
                    <option>INSTALLMENT</option>
                    <option>RENTAL</option>
                    <option>FEE</option>
                  </select>
                </td>
                <td><input className="input" value={it.qty} onChange={e=>updateItem(idx,'qty',e.target.value)} /></td>
                <td><input className="input" value={it.unit_price} onChange={e=>updateItem(idx,'unit_price',e.target.value)} /></td>
                <td><input className="input" value={it.monthly_amount} onChange={e=>updateItem(idx,'monthly_amount',e.target.value)} /></td>
                <td><button className="btn secondary" onClick={()=>removeItem(idx)}>Remove</button></td>
              </tr>
            ))}
            <tr><td colSpan={6}><button className="btn secondary" onClick={addItem}>Add Item</button></td></tr>
          </tbody>
        </table>

        <div className="hr" />
        <h3>Charges</h3>
        <div className="row">
          <div className="col"><label>Delivery Fee</label><input className="input" value={deliveryFee} onChange={e=>setDeliveryFee(e.target.value)} /></div>
          <div className="col"><label>Return Delivery Fee</label><input className="input" value={returnDeliveryFee} onChange={e=>setReturnDeliveryFee(e.target.value)} /></div>
        </div>

        <div className="hr" />
        <h3>Plan</h3>
        <div className="row">
          <div className="col"><label>Plan Type</label>
            <select className="select" value={planType} onChange={e=>setPlanType(e.target.value)}>
              <option value=""></option>
              <option>INSTALLMENT</option>
              <option>RENTAL</option>
            </select>
          </div>
          <div className="col"><label>Months</label><input className="input" type="number" value={planMonths} onChange={e=>setPlanMonths(e.target.value)} /></div>
          <div className="col"><label>Monthly Amount</label><input className="input" value={planMonthly} onChange={e=>setPlanMonthly(e.target.value)} /></div>
        </div>

        {err && <div style={{marginTop:8,color:'#ffb3b3'}}>{err}</div>}
        <div style={{marginTop:8}}><button className="btn" onClick={onCreate} disabled={busy || !custName || items.length===0}>Create Order</button></div>
      </div>
    </Layout>
  );
}

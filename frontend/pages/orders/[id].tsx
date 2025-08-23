import Layout from "@/components/Layout";
import React from "react";
import Link from "next/link";
import { useRouter } from "next/router";
import { getOrder, updateOrder, addPayment, voidPayment, voidOrder, markReturned, markBuyback, invoicePdfUrl, orderDue } from "@/utils/api";

export default function OrderDetailPage(){
  const router = useRouter();
  const { id } = router.query;
  const [order,setOrder] = React.useState<any>(null);
  const [msg,setMsg] = React.useState<string>("");
  const [err,setErr] = React.useState<string>("");
  const [busy,setBusy] = React.useState<boolean>(false);

  const [payAmt,setPayAmt] = React.useState<string>("");
  const [payDate,setPayDate] = React.useState<string>("");
  const [payMethod,setPayMethod] = React.useState<string>("");
  const [payRef,setPayRef] = React.useState<string>("");

  const [penalty,setPenalty] = React.useState<string>("");
  const [disc,setDisc] = React.useState<string>("");
  const [delFee,setDelFee] = React.useState<string>("");
  const [retDelFee,setRetDelFee] = React.useState<string>("");
  const [retCollect,setRetCollect] = React.useState<boolean>(false);
  const [retMethod,setRetMethod] = React.useState<string>("");
  const [retRef,setRetRef] = React.useState<string>("");
  const [notes,setNotes] = React.useState<string>("");
  const [deliveryDate,setDeliveryDate] = React.useState<string>("");

  const [planType,setPlanType] = React.useState<string>("");
  const [planMonths,setPlanMonths] = React.useState<string>("");
  const [planMonthly,setPlanMonthly] = React.useState<string>("");

  const [buybackAmt,setBuybackAmt] = React.useState<string>("");
  const [buybackDiscType,setBuybackDiscType] = React.useState<string>("");
  const [buybackDiscVal,setBuybackDiscVal] = React.useState<string>("");
  const [buybackMethod,setBuybackMethod] = React.useState<string>("");
  const [buybackRef,setBuybackRef] = React.useState<string>("");

  const [due,setDue] = React.useState<any>(null);
  const [asOf,setAsOf] = React.useState<string>("");

  function setError(e:any){ setErr(e?.message || "Failed"); }

  const loadDue = React.useCallback(async (orderId:number, date?:string) => {
    try{
      const d = await orderDue(orderId, date);
      setDue(d);
    }catch(e:any){ setError(e); }
  }, []);

  const load = React.useCallback(async () => {
    if(!id) return;
    try{
      const o = await getOrder(id as any);
      setOrder(o);
      setPenalty(String(o?.penalty_fee ?? ""));
      setDisc(String(o?.discount ?? ""));
      setDelFee(String(o?.delivery_fee ?? ""));
      setRetDelFee(String(o?.return_delivery_fee ?? ""));
      setNotes(String(o?.notes ?? ""));
      setDeliveryDate(o?.delivery_date ? (o.delivery_date as string).slice(0,10) : "");
      setPlanType(String(o?.plan?.plan_type ?? ""));
      setPlanMonths(o?.plan?.months ? String(o.plan.months) : "");
      setPlanMonthly(o?.plan?.monthly_amount ? String(o.plan.monthly_amount) : "");
    }catch(e:any){ setError(e); }
  }, [id]);

  React.useEffect(()=>{ load(); },[load]);

  React.useEffect(()=>{ if(order) loadDue(order.id, asOf); },[order, asOf, loadDue]);

  if(!order) return <Layout><div className="card">Loading...</div></Layout>;

  async function savePricing(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const patch:any = {
        penalty_fee: Number(penalty||0),
        discount: Number(disc||0),
        delivery_fee: Number(delFee||0),
        return_delivery_fee: Number(retDelFee||0),
        notes,
      };
      if(deliveryDate) patch.delivery_date = deliveryDate; // ISO
      if(planType || planMonths || planMonthly){
        patch.plan = {
          plan_type: planType || undefined,
          months: planMonths ? Number(planMonths) : undefined,
          monthly_amount: planMonthly ? Number(planMonthly) : undefined,
        };
      }
      const out = await updateOrder(order.id, patch);
      setMsg("Order updated"); setOrder(out);
      await loadDue(order.id, asOf);
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function postPayment(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const out = await addPayment({ order_id: order.id, amount: Number(payAmt||0), date: payDate || undefined, method: payMethod || undefined, reference: payRef || undefined, idempotencyKey: crypto.randomUUID() });
      setMsg("Payment added"); await load(); await loadDue(order.id, asOf);
      setPayAmt(""); setPayDate(""); setPayMethod(""); setPayRef("");
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function onVoidPayment(pid:number){
    setBusy(true); setErr(""); setMsg("");
    try{ await voidPayment(pid, "Voided from UI"); setMsg("Payment voided"); await load(); }
    catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function onCancelOrder(){
    if(!confirm("Void/cancel entire order?")) return;
    setBusy(true); setErr(""); setMsg("");
    try{ await voidOrder(order.id, "Cancelled from UI"); setMsg("Order cancelled"); await load(); }
    catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function onReturned(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const out = await markReturned(order.id, undefined, {
        collect: retCollect,
        return_delivery_fee: retDelFee ? Number(retDelFee) : undefined,
        method: retMethod || undefined,
        reference: retRef || undefined,
      });
      setOrder(out?.order || out);
      await loadDue(order.id, asOf);
      setMsg("Marked as returned");
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function onBuyback(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const opts:any = { method: buybackMethod || undefined, reference: buybackRef || undefined };
      if(buybackDiscType && buybackDiscVal){
        opts.discount = { type: buybackDiscType, value: Number(buybackDiscVal) };
      }
      const out = await markBuyback(order.id, Number(buybackAmt||0), opts);
      setOrder(out?.order || out);
      setBuybackAmt("");
      setBuybackDiscType("");
      setBuybackDiscVal("");
      setBuybackMethod("");
      setBuybackRef("");
      await loadDue(order.id, asOf);
      setMsg("Buyback recorded");
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  return (
    <Layout>
      <div className="row">
        <div className="col">
          <div className="card">
            <div style={{display:"flex",justifyContent:"space-between",alignItems:"center"}}>
              <h2 style={{marginTop:0}}>{order.code || order.id} <span className="badge">{order.status}</span></h2>
              <a className="btn secondary" href={invoicePdfUrl(order.id)} target="_blank" rel="noreferrer">
                Invoice PDF
              </a>
            </div>
            <div className="kv">
              <div>Type</div><div>{order.type}</div>
              <div>Customer</div><div>{order.customer?.name} ({order.customer?.phone})</div>
              <div>Address</div><div>{order.customer?.address}</div>
              <div>Delivery</div><div>{order.delivery_date ? String(order.delivery_date).slice(0,10) : "-"}</div>
            </div>

            <div className="hr" />
            <h3>Items</h3>
            <div style={{overflowX:"auto"}}>
              <table className="table">
                <thead><tr><th>Name</th><th>Type</th><th>Qty</th><th>Unit</th><th>Line Total</th></tr></thead>
                <tbody>
                  {(order.items||[]).map((it:any)=>(
                    <tr key={it.id || it.name}>
                      <td>{it.name}</td><td>{it.item_type}</td>
                      <td>{Number(it.qty||1)}</td>
                      <td>RM {Number(it.unit_price||0).toFixed(2)}</td>
                      <td>RM {Number(it.line_total||0).toFixed(2)}</td>
                    </tr>
                  ))}
                  {(order.items||[]).length===0 && <tr><td colSpan={5} style={{opacity:.7}}>No items</td></tr>}
                </tbody>
              </table>
            </div>

            <div className="hr" />
            <div style={{display:"flex",alignItems:"center",gap:8,marginBottom:8}}>
              <label>As of</label>
              <input className="input" type="date" value={asOf} onChange={e=>setAsOf(e.target.value)} />
            </div>
            <div className="kv">
              <div>Subtotal</div><div>RM {Number(order.subtotal||0).toFixed(2)}</div>
              <div>Delivery Fee</div><div>RM {Number(order.delivery_fee||0).toFixed(2)}</div>
              <div>Return Delivery Fee</div><div>RM {Number(order.return_delivery_fee||0).toFixed(2)}</div>
              <div>Penalty</div><div>RM {Number(order.penalty_fee||0).toFixed(2)}</div>
              <div>Discount</div><div>- RM {Number(order.discount||0).toFixed(2)}</div>
              <div>Total</div><div><b>RM {Number(order.total||0).toFixed(2)}</b></div>
              <div>Paid</div><div>RM {Number(order.paid_amount||0).toFixed(2)}</div>
              <div>Balance</div><div><b>RM {Number(order.balance||0).toFixed(2)}</b></div>
              {due && (<>
                <div>Accrued</div><div>RM {Number(due.accrued||0).toFixed(2)}</div>
                <div>Outstanding</div><div><b>RM {Number(due.outstanding||0).toFixed(2)}</b></div>
              </>)}
            </div>

            <div className="hr" />
            <div className="row">
              <div className="col">
                <button className="btn secondary" onClick={onCancelOrder} disabled={busy}>Void/Cancel Order</button>
              </div>
              <div className="col" style={{display:"flex",flexDirection:"column",gap:4}}>
                <label><input type="checkbox" checked={retCollect} onChange={e=>setRetCollect(e.target.checked)} /> Collect</label>
                <input className="input" placeholder="Return fee" value={retDelFee} onChange={e=>setRetDelFee(e.target.value)} />
                <input className="input" placeholder="Method" value={retMethod} onChange={e=>setRetMethod(e.target.value)} />
                <input className="input" placeholder="Reference" value={retRef} onChange={e=>setRetRef(e.target.value)} />
                <button className="btn secondary" onClick={onReturned} disabled={busy}>Mark Returned (Rental)</button>
              </div>
              <div className="col" style={{display:"flex",flexDirection:"column",gap:4}}>
                <input className="input" placeholder="Buyback amount" value={buybackAmt} onChange={e=>setBuybackAmt(e.target.value)} />
                <div style={{display:"flex",gap:4}}>
                  <select className="select" value={buybackDiscType} onChange={e=>setBuybackDiscType(e.target.value)}>
                    <option value="">No Discount</option>
                    <option value="percent">% Off</option>
                    <option value="fixed">Fixed</option>
                  </select>
                  <input className="input" placeholder="Value" value={buybackDiscVal} onChange={e=>setBuybackDiscVal(e.target.value)} />
                </div>
                <input className="input" placeholder="Method" value={buybackMethod} onChange={e=>setBuybackMethod(e.target.value)} />
                <input className="input" placeholder="Reference" value={buybackRef} onChange={e=>setBuybackRef(e.target.value)} />
                <button className="btn secondary" onClick={onBuyback} disabled={busy || !buybackAmt}>Record Buyback</button>
              </div>
            </div>

          </div>
        </div>
        <div className="col">
          <div className="card">
            <h3 style={{marginTop:0}}>Edit Pricing & Notes</h3>
            <div className="row">
              <div className="col">
                <label>Delivery Date</label>
                <input className="input" type="date" value={deliveryDate} onChange={e=>setDeliveryDate(e.target.value)} />
              </div>
              <div className="col"><label>Penalty Fee</label><input className="input" value={penalty} onChange={e=>setPenalty(e.target.value)} /></div>
              <div className="col"><label>Discount</label><input className="input" value={disc} onChange={e=>setDisc(e.target.value)} /></div>
            </div>
            <div className="row">
              <div className="col"><label>Delivery Fee</label><input className="input" value={delFee} onChange={e=>setDelFee(e.target.value)} /></div>
              <div className="col"><label>Return Delivery Fee</label><input className="input" value={retDelFee} onChange={e=>setRetDelFee(e.target.value)} /></div>
            </div>
            <div className="row">
              <div className="col">
                <label>Plan Type</label>
                <select className="select" value={planType} onChange={e=>setPlanType(e.target.value)}>
                  <option value="">None</option>
                  <option>INSTALLMENT</option>
                  <option>RENTAL</option>
                </select>
              </div>
              <div className="col"><label>Months</label><input className="input" type="number" value={planMonths} onChange={e=>setPlanMonths(e.target.value)} /></div>
              <div className="col"><label>Monthly Amount</label><input className="input" value={planMonthly} onChange={e=>setPlanMonthly(e.target.value)} /></div>
            </div>
            <div style={{marginTop:8}}>
              <label>Notes</label>
              <textarea className="textarea" rows={4} value={notes} onChange={e=>setNotes(e.target.value)} />
            </div>
            <div style={{marginTop:8}}><button className="btn" onClick={savePricing} disabled={busy}>Save</button></div>
          </div>

          <div className="card" style={{marginTop:16}}>
            <h3 style={{marginTop:0}}>Payments</h3>
            <div className="row">
              <div className="col"><input className="input" placeholder="Amount" value={payAmt} onChange={e=>setPayAmt(e.target.value)} /></div>
              <div className="col"><input className="input" type="date" placeholder="Date" value={payDate} onChange={e=>setPayDate(e.target.value)} /></div>
            </div>
            <div className="row">
              <div className="col"><input className="input" placeholder="Method" value={payMethod} onChange={e=>setPayMethod(e.target.value)} /></div>
              <div className="col"><input className="input" placeholder="Reference" value={payRef} onChange={e=>setPayRef(e.target.value)} /></div>
            </div>
            <div style={{marginTop:8}}><button className="btn" onClick={postPayment} disabled={busy || !payAmt}>Add Payment</button></div>

            <div className="hr" />
            <table className="table">
              <thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Ref</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {(order.payments||[]).map((p:any)=>(
                  <tr key={p.id}>
                    <td>{p.date}</td>
                    <td>RM {Number(p.amount||0).toFixed(2)}</td>
                    <td>{p.method||"-"}</td>
                    <td>{p.reference||"-"}</td>
                    <td><span className="badge">{p.status}</span></td>
                    <td>{p.status!=="VOIDED" && <button className="btn secondary" onClick={()=>onVoidPayment(p.id)} disabled={busy}>Void</button>}</td>
                  </tr>
                ))}
                {(!order.payments || order.payments.length===0) && <tr><td colSpan={6} style={{opacity:.7}}>No payments</td></tr>}
              </tbody>
            </table>
          </div>

          <div style={{marginTop:8,color: err? "#ffb3b3" : "#9fffba"}}>{err || msg}</div>
        </div>
      </div>
    </Layout>
  );
}

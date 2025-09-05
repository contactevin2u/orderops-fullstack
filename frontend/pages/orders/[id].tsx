import React from "react";
import Link from "next/link";
import Image from "next/image";
import { useRouter } from "next/router";
import { useTranslation } from "react-i18next";
import Card from "@/components/Card";
import { getOrder, updateOrder, addPayment, voidPayment, voidOrder, markReturned, markBuyback, invoicePrintUrl, orderDue, markSuccess, updateCommission } from "@/utils/api";

export default function OrderDetailPage(){
  const router = useRouter();
  const { id } = router.query;
  const { t } = useTranslation();
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
  const [editRetDelFee,setEditRetDelFee] = React.useState<string>("");
  const [retCollect,setRetCollect] = React.useState<boolean>(false);
  const [retMethod,setRetMethod] = React.useState<string>("");
  const [retRef,setRetRef] = React.useState<string>("");
  const [notes,setNotes] = React.useState<string>("");
  const [deliveryDate,setDeliveryDate] = React.useState<string>("");

  const [orderCode,setOrderCode] = React.useState<string>("");
  const [orderType,setOrderType] = React.useState<string>("");
  const [custName,setCustName] = React.useState<string>("");
  const [custPhone,setCustPhone] = React.useState<string>("");
  const [custAddress,setCustAddress] = React.useState<string>("");

  const [planType,setPlanType] = React.useState<string>("");
  const [planMonths,setPlanMonths] = React.useState<string>("");
  const [planMonthly,setPlanMonthly] = React.useState<string>("");

  const [items,setItems] = React.useState<any[]>([]);
  const [removedIds, setRemovedIds] = React.useState<number[]>([]);

  const [buybackAmt,setBuybackAmt] = React.useState<string>("");
  const [buybackDiscType,setBuybackDiscType] = React.useState<string>("");
  const [buybackDiscVal,setBuybackDiscVal] = React.useState<string>("");
  const [buybackMethod,setBuybackMethod] = React.useState<string>("");
  const [buybackRef,setBuybackRef] = React.useState<string>("");

  const [commission,setCommission] = React.useState<string>("");

  const [due,setDue] = React.useState<any>(null);
  const [asOf,setAsOf] = React.useState<string>("");

  function setError(e:any){ setErr(e?.message || "Failed"); }

  const loadDue = React.useCallback(async (orderId:number, date?:string) => {
    try{
      const d = await orderDue(orderId, date);
      setDue(d);
    }catch(e:any){ 
      console.error('Failed to load due amount:', e);
      setDue(null); 
    }
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
      setEditRetDelFee(String(o?.return_delivery_fee ?? ""));
      setNotes(String(o?.notes ?? ""));
      setDeliveryDate(o?.delivery_date ? (o.delivery_date as string).slice(0,10) : "");
      setOrderCode(String(o?.code ?? ""));
      setOrderType(String(o?.type ?? ""));
      setCustName(String(o?.customer?.name ?? ""));
      setCustPhone(String(o?.customer?.phone ?? ""));
      setCustAddress(String(o?.customer?.address ?? ""));
      setPlanType(String(o?.plan?.plan_type ?? ""));
      setPlanMonths(o?.plan?.months ? String(o.plan.months) : "");
      setPlanMonthly(o?.plan?.monthly_amount ? String(o.plan.monthly_amount) : "");
      setItems(o?.items ? o.items.map((it:any)=>({ ...it, qty: String(it.qty), monthly_amount: it.monthly_amount ? String(it.monthly_amount) : "" })) : []);
      setCommission(o?.trip?.commission && o.trip.commission.computed_amount !== undefined ? String(o.trip.commission.computed_amount) : "");
    }catch(e:any){ setError(e); }
  }, [id]);

  React.useEffect(()=>{ load(); },[load]);

  React.useEffect(()=>{ if(order) loadDue(order.id, asOf); },[order, asOf, loadDue]);

  if(!order) return <Card aria-busy="true">Loading order...</Card>;
  const profile = order.company_profile || {};
  const invoiceUrl = invoicePrintUrl(order.id);
  function copyInvoice(){
    navigator.clipboard.writeText(invoiceUrl);
    setMsg(t('documents.copied'));
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
    const item = items[idx];
    if(item?.id) setRemovedIds([...removedIds, item.id]);
    setItems(items.filter((_,i)=>i!==idx));
  }

  async function saveItems(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const patchItems = items.map((it:any)=>({
        ...(it.id ? { id: it.id } : {}),
        name: it.name,
        item_type: it.item_type,
        qty: Number(it.qty||0),
        unit_price: Number(it.unit_price||0),
        line_total: Number(it.unit_price||0) * Number(it.qty||0),
        ...(it.monthly_amount ? { monthly_amount: Number(it.monthly_amount||0) } : {}),
      }));
      const payload:any = { items: patchItems };
      if(removedIds.length) payload.delete_items = removedIds;
      const out = await updateOrder(order.id, payload);
      setMsg("Items updated");
      setOrder(out);
      setItems(out?.items ? out.items.map((it:any)=>({ ...it, qty: String(it.qty), monthly_amount: it.monthly_amount ? String(it.monthly_amount) : "" })) : []);
      setRemovedIds([]);
      await loadDue(order.id, asOf);
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function saveDetails(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const patch:any = {
        code: orderCode || undefined,
        type: orderType || undefined,
        customer: {
          name: custName,
          phone: custPhone || undefined,
          address: custAddress || undefined,
        },
        penalty_fee: Number(penalty||0),
        discount: Number(disc||0),
        delivery_fee: Number(delFee||0),
        return_delivery_fee: Number(editRetDelFee||0),
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
    if(!confirm("Void this payment?")) return;
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
      // Get current outstanding amount using proper calculation
      const d = due || await orderDue(order.id, asOf);
      
      // For RENTAL orders, validate outstanding is cleared unless collect=true
      if(order.type === 'RENTAL' && !retCollect && d && Number(d?.balance || 0) > 0){
        setErr(`Outstanding balance of RM ${Number(d.balance || 0).toFixed(2)} must be cleared before return. Check 'Collect' to collect fees during return.`);
        setBusy(false);
        return;
      }
      
      const out = await markReturned(order.id, undefined, {
        collect: retCollect,
        return_delivery_fee: retDelFee ? Number(retDelFee) : undefined,
        method: retMethod || undefined,
        reference: retRef || undefined,
      });
      
      setOrder(out?.order || out);
      await loadDue(order.id, asOf);
      setMsg("Marked as returned successfully");
    }catch(e:any){ 
      setError(e); 
    } finally{ 
      setBusy(false); 
    }
  }

  async function onSuccess(){
    setBusy(true); setErr(""); setMsg("");
    try{
      await markSuccess(order.id);
      setMsg("Marked success");
      await load();
    }catch(e:any){ setError(e); } finally{ setBusy(false); }
  }

  async function saveCommission(){
    setBusy(true); setErr(""); setMsg("");
    try{
      await updateCommission(order.id, Number(commission||0));
      setMsg("Commission updated");
      await load();
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
        <>
        <Link href="/orders" className="btn secondary mb-4">&larr; Back to Orders</Link>
        <div className="grid items-start gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(300px,1fr)]">
          <div>
            <Card>
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h2 className="m-0">
                {order.code || order.id} 
                <span className="badge">{order.status}</span>
                {order.trip && (
                  <span className="badge" style={{ marginLeft: '8px', backgroundColor: order.trip.status === 'DELIVERED' ? '#10b981' : order.trip.status === 'IN_TRANSIT' ? '#f59e0b' : '#6b7280' }}>
                    Trip: {order.trip.status}
                  </span>
                )}
              </h2>
              <a className="btn secondary" href={invoicePrintUrl(order.id)} target="_blank" rel="noreferrer">
                Invoice PDF
              </a>
            </div>
            <div className="kv">
              <div>Type</div><div>{order.type}</div>
              <div>Customer</div>
              <div>
                {order.customer?.name}
                {order.customer?.phone && (
                  <> (<a href={`tel:${order.customer.phone}`}>{order.customer.phone}</a>)</>
                )}
              </div>
              <div>Address</div><div>{order.customer?.address}</div>
              <div>Delivery</div><div>{order.delivery_date ? String(order.delivery_date).slice(0,10) : "-"}</div>
            </div>

            <div className="hr" />
              <h3 className="m-0">Items</h3>
              <div className="overflow-x-auto">
                <table className="table">
                  <thead><tr><th>Name</th><th>Type</th><th>Qty</th><th>Unit</th><th>Monthly</th><th>Line Total</th><th></th></tr></thead>
                  <tbody>
                    {items.map((it:any,idx:number)=>(
                      <tr key={it.id || idx}>
                        <td><input className="input" value={it.name} onChange={e=>updateItem(idx,'name',e.target.value)} /></td>
                        <td>
                          <select className="select" value={it.item_type} onChange={e=>updateItem(idx,'item_type',e.target.value)}>
                            <option>OUTRIGHT</option>
                            <option>INSTALLMENT</option>
                            <option>RENTAL</option>
                            <option>FEE</option>
                          </select>
                        </td>
                        <td><input className="input" type="number" min="1" step="1" value={it.qty} onChange={e=>updateItem(idx,'qty',e.target.value)} /></td>
                        <td><input className="input" type="number" min="0" step="0.01" value={it.unit_price} onChange={e=>updateItem(idx,'unit_price',e.target.value)} /></td>
                        <td><input className="input" type="number" min="0" step="0.01" value={it.monthly_amount} onChange={e=>updateItem(idx,'monthly_amount',e.target.value)} /></td>
                        <td>RM {(Number(it.unit_price||0)*Number(it.qty||0)).toFixed(2)}</td>
                        <td><button className="btn secondary" onClick={()=>removeItem(idx)}>Remove</button></td>
                      </tr>
                    ))}
                    {items.length===0 && <tr><td colSpan={7} className="opacity-70">No items</td></tr>}
                    <tr><td colSpan={7}><button className="btn secondary" onClick={addItem}>Add Item</button></td></tr>
                  </tbody>
                </table>
              </div>
              <div className="mt-2"><button className="btn" onClick={saveItems} disabled={busy}>Save Items</button></div>

            <div className="hr" />
            <div className="flex items-center gap-2 mb-2">
              <label className="flex-shrink-0">As of</label>
              <input
                className="input flex-1 w-auto"
                type="date"
                value={asOf}
                onChange={e=>setAsOf(e.target.value)}
              />
            </div>
            <div className="kv">
              <div>Subtotal</div><div>RM {Number(order.subtotal||0).toFixed(2)}</div>
              <div>Delivery Fee</div><div>RM {Number(order.delivery_fee||0).toFixed(2)}</div>
              <div>Return Delivery Fee</div><div>RM {Number(order.return_delivery_fee||0).toFixed(2)}</div>
              <div>Penalty</div><div>RM {Number(order.penalty_fee||0).toFixed(2)}</div>
              <div>Discount</div><div>- RM {Number(order.discount||0).toFixed(2)}</div>
              <div>Total</div><div><b>RM {Number(order.total||0).toFixed(2)}</b></div>
              <div>Paid</div><div>RM {Number(order.paid_amount||0).toFixed(2)}</div>
              {due && (<>
                <div>Expected</div><div>RM {Number(due.expected||0).toFixed(2)}</div>
                <div>Accrued</div><div>RM {Number(due.accrued||0).toFixed(2)}</div>
                <div>Outstanding</div><div><b>RM {Number(due.balance||0).toFixed(2)}</b></div>
              </>)}
            </div>

            <div className="hr" />
            <div className="row">
              <div className="col">
                <button className="btn secondary" onClick={onCancelOrder} disabled={busy}>Void/Cancel Order</button>
              </div>
              <div className="col flex flex-col gap-1">
                <label><input type="checkbox" checked={retCollect} onChange={e=>setRetCollect(e.target.checked)} /> Collect</label>
                <input className="input" type="number" min="0" step="0.01" placeholder="Return fee" value={retDelFee} onChange={e=>setRetDelFee(e.target.value)} />
                <input className="input" placeholder="Method" value={retMethod} onChange={e=>setRetMethod(e.target.value)} />
                <input className="input" placeholder="Reference" value={retRef} onChange={e=>setRetRef(e.target.value)} />
                <button className="btn secondary" onClick={onReturned} disabled={busy}>Mark Returned (Rental)</button>
              </div>
              <div className="col flex flex-col gap-1">
                <input
                  className="input"
                  type="number"
                  min="0"
                  step="0.01"
                  placeholder="Buyback amount"
                  value={buybackAmt}
                  onChange={e=>setBuybackAmt(e.target.value)}
                />
                <div className="flex gap-1">
                  <select
                    className="select flex-1 w-auto"
                    value={buybackDiscType}
                    onChange={e=>setBuybackDiscType(e.target.value)}
                  >
                    <option value="">No Discount</option>
                    <option value="percent">% Off</option>
                    <option value="fixed">Fixed</option>
                  </select>
                  <input
                    className="input flex-1 w-auto"
                    type="number"
                    min="0"
                    step="0.01"
                    placeholder="Value"
                    value={buybackDiscVal}
                    onChange={e=>setBuybackDiscVal(e.target.value)}
                  />
                </div>
                <input className="input" placeholder="Method" value={buybackMethod} onChange={e=>setBuybackMethod(e.target.value)} />
                <input className="input" placeholder="Reference" value={buybackRef} onChange={e=>setBuybackRef(e.target.value)} />
                <button className="btn secondary" onClick={onBuyback} disabled={busy || !buybackAmt}>Record Buyback</button>
              </div>
            </div>
          </Card>
        </div>
        <div className="space-y-4 lg:sticky lg:top-2">
          <Card>
            <h3 className="m-0">Edit Order</h3>
            <div className="row">
              <div className="col"><label>Order Code</label><input className="input" value={orderCode} onChange={e=>setOrderCode(e.target.value)} /></div>
              <div className="col"><label>Type</label>
                <select className="select" value={orderType} onChange={e=>setOrderType(e.target.value)}>
                  <option>OUTRIGHT</option>
                  <option>INSTALLMENT</option>
                  <option>RENTAL</option>
                  <option>MIXED</option>
                </select>
              </div>
            </div>
            <div className="row">
              <div className="col"><label>Customer Name</label><input className="input" value={custName} onChange={e=>setCustName(e.target.value)} /></div>
              <div className="col"><label>Phone</label><input className="input" value={custPhone} onChange={e=>setCustPhone(e.target.value)} /></div>
            </div>
            <div className="mt-2"><label>Address</label><textarea className="textarea" rows={2} value={custAddress} onChange={e=>setCustAddress(e.target.value)} /></div>
            <div className="row">
              <div className="col">
                <label>Delivery Date</label>
                <input className="input" type="date" value={deliveryDate} onChange={e=>setDeliveryDate(e.target.value)} />
              </div>
              <div className="col"><label>Penalty Fee</label><input className="input" type="number" min="0" step="0.01" value={penalty} onChange={e=>setPenalty(e.target.value)} /></div>
              <div className="col"><label>Discount</label><input className="input" type="number" min="0" step="0.01" value={disc} onChange={e=>setDisc(e.target.value)} /></div>
            </div>
            <div className="row">
              <div className="col"><label>Delivery Fee</label><input className="input" type="number" min="0" step="0.01" value={delFee} onChange={e=>setDelFee(e.target.value)} /></div>
              <div className="col"><label>Return Delivery Fee</label><input className="input" type="number" min="0" step="0.01" value={editRetDelFee} onChange={e=>setEditRetDelFee(e.target.value)} /></div>
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
              <div className="col"><label>Months</label><input className="input" type="number" min="1" step="1" value={planMonths} onChange={e=>setPlanMonths(e.target.value)} /></div>
              <div className="col"><label>Monthly Amount</label><input className="input" type="number" min="0" step="0.01" value={planMonthly} onChange={e=>setPlanMonthly(e.target.value)} /></div>
            </div>
            <div className="mt-2">
              <label>Notes</label>
              <textarea className="textarea" rows={4} value={notes} onChange={e=>setNotes(e.target.value)} />
            </div>
            <div className="mt-2"><button className="btn" onClick={saveDetails} disabled={busy}>Save</button></div>
          </Card>

          <Card>
            <h3 className="m-0">{t('documents.title')}</h3>
            <div className="row mb-2">
              <a className="btn" href={invoiceUrl} target="_blank" rel="noopener noreferrer">{t('documents.view')}</a>
              <a className="btn secondary" href={invoiceUrl} download>{t('documents.download')}</a>
              <button className="btn secondary" onClick={copyInvoice}>{t('documents.share')}</button>
            </div>
            <Card className="mt-2">
              {profile.logo_url ? (
                <Image
                  src={profile.logo_url}
                  alt="logo"
                  width={160}
                  height={40}
                  className="max-h-10 w-auto"
                />
              ) : (
                <div>{t('documents.noLogo')}</div>
              )}
              <p>{profile.address || t('documents.noAddress')}</p>
              <p>{profile.tax_label ? `${profile.tax_label} ${profile.tax_percent || ''}%` : t('documents.noTax')}</p>
              <p>{profile.bank_account || t('documents.noBank')}</p>
              <p>{profile.footer_note || t('documents.noFooter')}</p>
            </Card>
          </Card>

          <Card>
            <h3 className="m-0">Payments</h3>
            <div className="row">
              <div className="col"><input className="input" type="number" min="0" step="0.01" placeholder="Amount" value={payAmt} onChange={e=>setPayAmt(e.target.value)} /></div>
              <div className="col"><input className="input" type="date" placeholder="Date" value={payDate} onChange={e=>setPayDate(e.target.value)} /></div>
            </div>
            <div className="row">
              <div className="col"><input className="input" placeholder="Method" value={payMethod} onChange={e=>setPayMethod(e.target.value)} /></div>
              <div className="col"><input className="input" placeholder="Reference" value={payRef} onChange={e=>setPayRef(e.target.value)} /></div>
            </div>
            <div className="mt-2"><button className="btn" onClick={postPayment} disabled={busy || !payAmt}>Add Payment</button></div>

            <div className="hr" />
            <table className="table">
              <thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Ref</th><th>Status</th><th>Actions</th></tr></thead>
              <tbody>
                {(order.payments||[]).map((p:any)=>(
                  <tr key={p.id}>
                    <td>{p.date}</td>
                    <td>RM {Number(p.amount||0).toFixed(2)}</td>
                    <td>{p.method||"-"}</td>
                    <td>{p.reference||"-"}</td>
                    <td><span className="badge">{p.status}</span></td>
                    <td className="cluster">
                      <button 
                        className="btn secondary" 
                        onClick={()=>window.open(`/_api/payments/${p.id}/receipt.pdf`, '_blank')}
                        disabled={busy}
                      >
                        Receipt
                      </button>
                      {p.status!=="VOIDED" && 
                        <button className="btn secondary" onClick={()=>onVoidPayment(p.id)} disabled={busy}>
                          Void
                        </button>
                      }
                    </td>
                  </tr>
                ))}
                {(!order.payments || order.payments.length===0) && <tr><td colSpan={6} className="opacity-70">No payments</td></tr>}
              </tbody>
            </table>
          </Card>

            <Card>
              <h3 className="m-0">Delivery & Commission</h3>
              {order.trip?.status === "DELIVERED" && (
                <button className="btn mb-2" onClick={onSuccess} disabled={busy}>Mark Success</button>
              )}
              
              {order.trip && (
                <div className="space-y-2">
                  <div>
                    <label className="block text-sm font-medium mb-1">Driver Commission (RM)</label>
                    <input 
                      className="input" 
                      type="number" 
                      min="0" 
                      step="0.01" 
                      placeholder="Enter commission amount" 
                      value={commission} 
                      onChange={e=>setCommission(e.target.value)} 
                    />
                    <button className="btn mt-2 w-full" onClick={saveCommission} disabled={busy || !commission}>
                      {order.trip?.commission ? 'Update Commission' : 'Set Commission'}
                    </button>
                  </div>
                  
                  {order.trip?.commission && (
                    <div className="bg-gray-50 p-3 rounded text-sm">
                      <div><strong>Current:</strong> RM {order.trip.commission.computed_amount}</div>
                      <div><strong>Scheme:</strong> {order.trip.commission.scheme}</div>
                      <div><strong>Status:</strong> {order.trip.commission.actualized_at ? 'Released' : 'Pending'}</div>
                      {order.trip.commission.actualized_at && (
                        <div><strong>Released:</strong> {new Date(order.trip.commission.actualized_at).toLocaleDateString()}</div>
                      )}
                    </div>
                  )}
                  
                  {order.trip.pod_photo_urls && order.trip.pod_photo_urls.length > 0 && (
                    <div>
                      <label className="block text-sm font-medium mb-2">Proof of Delivery Photos</label>
                      <div className="flex flex-wrap gap-2">
                        {order.trip.pod_photo_urls.map((url: string, index: number) => (
                          <img
                            key={index}
                            src={url}
                            alt={`POD Photo ${index + 1}`}
                            className="w-20 h-20 object-cover rounded border cursor-pointer hover:opacity-75"
                            onClick={() => window.open(url, '_blank')}
                          />
                        ))}
                      </div>
                      <p className="text-xs text-gray-500 mt-1">Click photos to view full size</p>
                    </div>
                  )}
                </div>
              )}
              
              {!order.trip && (
                <div className="text-gray-500 text-sm">
                  No trip assigned yet. Commission can be set after driver assignment.
                </div>
              )}
            </Card>

          <div className={`mt-2 ${err ? 'text-red-300' : 'text-green-300'}`} aria-live="polite">{err || msg}</div>
        </div>
        </div>
        </>
    );
  }

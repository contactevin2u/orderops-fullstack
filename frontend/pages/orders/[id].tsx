import Layout from "@/components/Layout";
import { useRouter } from "next/router";
import useSWR from "swr";
import { addPayment, getOrder, invoicePdfUrl, updateOrder, voidOrder, voidPayment } from "@/utils/api";
import { useEffect, useState } from "react";
import OrderForm from "@/components/OrderForm";

export default function OrderDetailPage() {
  const router = useRouter();
  const id = router.query.id as string | undefined;
  const { data: order, error, isLoading, mutate } = useSWR(id ? `orders/${id}` : null, () => getOrder(id!));
  const [msg, setMsg] = useState<string| null>(null);

  useEffect(()=>{ if (error) setMsg(String(error)); }, [error]);

  async function postPayment() {
    setMsg(null);
    try {
      const amountRaw = prompt("Amount (RM)?", "0");
      if (!amountRaw) return;
      const amount = Number(amountRaw);
      const date = prompt("Date (YYYY-MM-DD, optional)?") || undefined;
      const method = prompt("Method (CASH/FPX/OTHER)?") || undefined;
      const reference = prompt("Reference (optional)?") || undefined;
      await addPayment({ order_id: Number(id), amount, date, method, reference, category: "ORDER" });
      await mutate();
      setMsg("Payment posted.");
    } catch (e:any) {
      setMsg(e.message || "Failed");
    }
  }

  async function doVoidPayment(pid: number) {
    const reason = prompt("Reason for void?") || "";
    try {
      await voidPayment(pid, reason);
      await mutate();
      setMsg("Payment voided.");
    } catch (e:any) { setMsg(e.message || "Failed"); }
  }

  async function doVoidOrder() {
    const reason = prompt("Reason to void/cancel order?") || "";
    try {
      try { await voidOrder(Number(id), reason); }
      catch { await updateOrder(Number(id), { status: "CANCELLED", void_reason: reason }); }
      await mutate();
      setMsg("Order voided/cancelled.");
    } catch (e:any) { setMsg(e.message || "Failed"); }
  }

  async function setStatus(s: string) {
    try {
      await updateOrder(Number(id), { status: s });
      await mutate();
      setMsg(`Status -> ${s}`);
    } catch (e:any) { setMsg(e.message || "Failed"); }
  }

  async function applyFees() {
    const delivery = Number(prompt("Delivery fee RM", String(order?.delivery_fee ?? 0)) || 0);
    const returnFee = Number(prompt("Return delivery fee RM", String(order?.return_delivery_fee ?? 0)) || 0);
    const penalty = Number(prompt("Penalty RM", String(order?.penalty_fee ?? 0)) || 0);
    const discount = Number(prompt("Discount RM", String(order?.discount ?? 0)) || 0);
    try {
      await updateOrder(Number(id), { delivery_fee: delivery, return_delivery_fee: returnFee, penalty_fee: penalty, discount });
      await mutate();
      setMsg("Charges updated.");
    } catch (e:any) { setMsg(e.message || "Failed"); }
  }

  if (!id) return <Layout><div>Loading...</div></Layout>;
  if (isLoading) return <Layout><div>Loading...</div></Layout>;

  return (
    <Layout>
      <h2 style={{marginTop:0}}>Order #{order?.code}</h2>
      {msg && <div className="card" style={{marginBottom:8}}>{msg}</div>}
      {error && <div style={{color:"var(--err)"}}>{String(error)}</div>}
      {!order ? (<div>Not found</div>) : (
        <>
          <div className="row">
            <div className="col">
              <div className="card">
                <h3 style={{marginTop:0}}>Summary</h3>
                <div><b>Customer:</b> {order.customer?.name} <small>({order.customer?.phone})</small></div>
                <div><b>Type:</b> {order.type} <span className="badge">{order.status}</span></div>
                <div><b>Total:</b> RM {Number(order.total||0).toFixed(2)} | <b>Paid:</b> RM {Number(order.paid_amount||0).toFixed(2)} | <b>Balance:</b> RM {Number(order.balance||0).toFixed(2)}</div>
                <div style={{marginTop:8, display:'flex', gap:8, flexWrap:'wrap'}}>
                  <button className="btn ok" onClick={postPayment}>Add Payment</button>
                  <button className="btn warn" onClick={applyFees}>Fees/Discount</button>
                  <a className="btn ghost" target="_blank" rel="noreferrer" href={invoicePdfUrl(Number(id))}>Invoice PDF</a>
                  <button className="btn err" onClick={doVoidOrder}>Void Order</button>
                  <button className="btn ghost" onClick={()=>setStatus("RETURNED")}>Mark Returned (Rental)</button>
                  <button className="btn ghost" onClick={()=>setStatus("BUYBACK")}>Mark Buyback</button>
                </div>
              </div>
            </div>
            <div className="col">
              <div className="card">
                <h3 style={{marginTop:0}}>Edit (inline)</h3>
                <OrderForm orderId={Number(id)} onSaved={()=>mutate()} />
              </div>
            </div>
          </div>

          <div className="card" style={{marginTop:12}}>
            <h3 style={{marginTop:0}}>Items</h3>
            <table className="table">
              <thead><tr><th>Name</th><th>Type</th><th>Qty</th><th>Unit</th><th>Total</th></tr></thead>
              <tbody>
                {(order.items||[]).map((it:any)=> (
                  <tr key={it.id}>
                    <td>{it.name}</td>
                    <td>{it.item_type}</td>
                    <td>{Number(it.qty||0)}</td>
                    <td>RM {Number(it.unit_price||0).toFixed(2)}</td>
                    <td>RM {Number(it.line_total||0).toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="card" style={{marginTop:12}}>
            <h3 style={{marginTop:0}}>Payments</h3>
            <table className="table">
              <thead><tr><th>Date</th><th>Amount</th><th>Method</th><th>Status</th><th></th></tr></thead>
              <tbody>
                {(order.payments||[]).map((p:any)=> (
                  <tr key={p.id}>
                    <td>{p.date}</td>
                    <td>RM {Number(p.amount||0).toFixed(2)}</td>
                    <td>{p.method || "-"}</td>
                    <td>{p.status}</td>
                    <td>
                      {p.status !== "VOIDED" && (
                        <button className="btn err" onClick={()=>doVoidPayment(p.id)}>Void</button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </Layout>
  );
}

import React from "react";
import Link from "next/link";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import {
  listOrders,
  markReturned,
  cancelInstallment,
  markBuyback,
  orderDue,
} from "@/lib/api";

type Tab = 'return' | 'cancel' | 'buyback';

export default function AdjustmentsPage() {
  const [tab, setTab] = React.useState<Tab>('return');
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<any[]>([]);
  const [order, setOrder] = React.useState<any>(null);
  const [msg, setMsg] = React.useState("");
  const [err, setErr] = React.useState("");
  const [beforeDue, setBeforeDue] = React.useState<any>(null);
  const [afterDue, setAfterDue] = React.useState<any>(null);

  React.useEffect(() => {
    if (!q) { setResults([]); return; }
    const t = setTimeout(async () => {
      try {
        const r = await listOrders(q, undefined, undefined, 20);
        setResults(r.items || []);
      } catch (e: any) {
        setErr(e?.message || "Search failed");
      }
    }, 300);
    return () => clearTimeout(t);
  }, [q]);

  const selectOrder = async (o: any) => {
    setOrder(o);
    setResults([]);
    setQ("");
    try {
      const d = await orderDue(o.id);
      setBeforeDue(d);
      setAfterDue(d);
    } catch (e: any) {
      setErr(e?.message || "Failed to load due");
    }
  };

  const submit = async () => {
    if (!order) return;
    setErr(""); setMsg("");
    try {
      if (tab === 'return') {
        if (beforeDue && Number(beforeDue.balance || 0) > 0 && (order.type === 'RENTAL' || !collect)) {
          setErr('Outstanding must be cleared before return');
          return;
        }
        await markReturned(order.id, retDate || undefined, {
          collect: collect,
          return_delivery_fee: rfee ? Number(rfee) : undefined,
          method,
          reference: reference,
        });
      } else if (tab === 'cancel') {
        await cancelInstallment(order.id, {
          penalty: penalty ? Number(penalty) : undefined,
          return_delivery_fee: rfee ? Number(rfee) : undefined,
          collect,
          method,
          reference,
        });
      } else {
        const opts: any = { method, reference };
        if (dtype && dval) opts.discount = { type: dtype, value: Number(dval) };
        await markBuyback(order.id, Number(amount || 0), opts);
      }
      const d = await orderDue(order.id);
      setAfterDue(d);
      setMsg(`Done. View order `);
    } catch (e: any) {
      setErr(e?.message || "Failed");
    }
  };

  const [collect, setCollect] = React.useState(false);
  const [penalty, setPenalty] = React.useState("");
  const [rfee, setRfee] = React.useState("");
  const [amount, setAmount] = React.useState("");
  const [dtype, setDtype] = React.useState("");
  const [dval, setDval] = React.useState("");
  const [method, setMethod] = React.useState("");
  const [reference, setReference] = React.useState("");
  const [retDate, setRetDate] = React.useState(() =>
    new Date().toISOString().slice(0, 10)
  );

  return (
      <div className="stack" style={{ maxWidth: 600, margin: '0 auto' }}>
        <PageHeader title="Adjustments" />
        <Card className="stack">
        <div className="cluster">
          <button className={`btn ${tab==='return'?'':'secondary'}`} onClick={()=>setTab('return')}>Return</button>
          <button className={`btn ${tab==='cancel'?'':'secondary'}`} onClick={()=>setTab('cancel')}>Cancel Installment</button>
          <button className={`btn ${tab==='buyback'?'':'secondary'}`} onClick={()=>setTab('buyback')}>Buyback</button>
        </div>
        {!order && (
          <div className="stack">
            <input className="input" placeholder="Search order" value={q} onChange={e=>setQ(e.target.value)} />
            {results.length>0 && (
              <ul className="stack" style={{maxHeight:200,overflowY:'auto'}}>
                {results.map(r=> (
                  <li key={r.id}>
                    <button className="btn secondary" style={{width:'100%'}} onClick={()=>selectOrder(r)}>
                      {r.code || r.id} - {r.customer_name}
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
        {order && (
          <div className="stack">
            <div className="cluster">
              <b>{order.code || order.id}</b> - {order.customer_name}
              <button className="btn secondary" onClick={()=>setOrder(null)}>Change</button>
            </div>
            {beforeDue && (
              <div>
                Outstanding: RM {Number(beforeDue?.balance || 0).toFixed(2)}
                {afterDue && (
                  <>
                    {" -> "}
                    {Number(afterDue?.balance || 0).toFixed(2)}
                    {" (Δ "}
                    {Number((afterDue?.balance || 0) - (beforeDue?.balance || 0)).toFixed(2)}
                    {")"}
                  </>
                )}
              </div>
            )}
            {tab !== 'buyback' && (
              <label><input type="checkbox" checked={collect} onChange={e=>setCollect(e.target.checked)} /> Collect</label>
            )}
            {tab === 'return' && (
              <input className="input" type="date" value={retDate} onChange={e=>setRetDate(e.target.value)} />
            )}
            {tab === 'cancel' && (
              <input className="input" placeholder="Penalty" value={penalty} onChange={e=>setPenalty(e.target.value)} />
            )}
            {tab !== 'buyback' && (
              <input className="input" placeholder="Return fee" value={rfee} onChange={e=>setRfee(e.target.value)} />
            )}
            {tab === 'buyback' && (
              <>
                <input className="input" placeholder="Amount" value={amount} onChange={e=>setAmount(e.target.value)} />
                <div className="cluster">
                  <select className="select" value={dtype} onChange={e=>setDtype(e.target.value)}>
                    <option value="">No Discount</option>
                    <option value="percent">% Off</option>
                    <option value="fixed">Fixed</option>
                  </select>
                  <input className="input" placeholder="Value" value={dval} onChange={e=>setDval(e.target.value)} />
                </div>
              </>
            )}
            <input className="input" placeholder="Method" value={method} onChange={e=>setMethod(e.target.value)} />
            <input className="input" placeholder="Reference" value={reference} onChange={e=>setReference(e.target.value)} />
            <button className="btn" onClick={submit}>
              Submit
            </button>
            {msg && order && (
              <div className="cluster">
                {msg}
                <Link href={`/orders/${order.id}`}>View order</Link>
              </div>
            )}
            {err && <div style={{color:'#ffb3b3'}}>{err}</div>}
          </div>
        )}
        </Card>
      </div>
  );
}


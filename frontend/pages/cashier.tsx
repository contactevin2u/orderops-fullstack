import Layout from "@/components/Layout";
import React from "react";
import { listOrders, orderDue, addPayment } from "@/utils/api";

export default function CashierPage() {
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<any[]>([]);
  const [selected, setSelected] = React.useState<any>(null);
  const [amount, setAmount] = React.useState("");
  const [date, setDate] = React.useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [due, setDue] = React.useState<any>(null);
  const [msg, setMsg] = React.useState("");
  const [err, setErr] = React.useState("");

  React.useEffect(() => {
    if (!q) {
      setResults([]);
      return;
    }
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
    setSelected(o);
    try {
      const d = await orderDue(o.id, date);
      setDue(d);
    } catch (e: any) {
      setErr(e?.message || "Failed to load due");
    }
  };

  const postPayment = async () => {
    if (!selected) return;
    setErr("");
    setMsg("");
    try {
      await addPayment({
        order_id: selected.id,
        amount: Number(amount || 0),
        date,
        idempotencyKey: crypto.randomUUID(),
      });
      const d = await orderDue(selected.id, date);
      setDue(d);
      setAmount("");
      setMsg("Payment recorded");
    } catch (e: any) {
      setErr(e?.message || "Failed to post");
    }
  };

  return (
    <Layout>
      <div className="card" style={{ maxWidth: 500, margin: '0 auto' }}>
        <h2 style={{ marginTop: 0 }}>Cashier</h2>
        <input
          className="input"
          placeholder="Search order..."
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        {results.length > 0 && (
          <ul className="stack" style={{ maxHeight: 200, overflowY: 'auto' }}>
            {results.map((r) => (
              <li key={r.id}>
                <button
                  className="btn secondary"
                  style={{ width: '100%' }}
                  onClick={() => selectOrder(r)}
                >
                  {r.code || r.id} - {r.customer_name}
                </button>
              </li>
            ))}
          </ul>
        )}
        {selected && (
          <div className="stack" style={{ marginTop: 16 }}>
            <div>
              <b>{selected.code || selected.id}</b> - {selected.customer_name}
            </div>
            <div>Due: RM {Number(due?.balance || 0).toFixed(2)}</div>
            <input
              className="input"
              style={{ fontSize: 24 }}
              placeholder="Amount"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
            <div style={{ display: 'flex', gap: 8 }}>
              <input
                className="input"
                type="date"
                value={date}
                onChange={(e) => setDate(e.target.value)}
              />
              <button className="btn secondary" onClick={() => setDate(new Date().toISOString().slice(0,10))}>Today</button>
            </div>
            <button className="btn" onClick={postPayment} disabled={!amount}>
              Add Payment
            </button>
          </div>
        )}
        <div style={{ marginTop: 8, color: err ? '#ffb3b3' : '#9fffba' }}>
          {err || msg}
        </div>
      </div>
    </Layout>
  );
}


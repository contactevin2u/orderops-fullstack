import React from "react";
import Link from "next/link";
import Card from "@/components/Card";
import {
  listOrders,
  orderDue,
  addPayment,
  voidPayment,
  exportPayments,
} from "@/utils/api";

export default function CashierPage() {
  const [q, setQ] = React.useState("");
  const [results, setResults] = React.useState<any[]>([]);
  const [order, setOrder] = React.useState<any>(null);
  const [due, setDue] = React.useState<any>(null);

  const [amount, setAmount] = React.useState("");
  const [method, setMethod] = React.useState("");
  const [date, setDate] = React.useState(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [reference, setReference] = React.useState("");
  const [category, setCategory] = React.useState("");

  const [msg, setMsg] = React.useState("");
  const [err, setErr] = React.useState("");

  const amountRef = React.useRef<HTMLInputElement>(null);
  const lastPaymentId = React.useRef<number | null>(null);

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

  const refreshDue = React.useCallback(async (id: number) => {
    try {
      const d = await orderDue(id, date);
      setDue(d);
    } catch (e: any) {
      setErr(e?.message || "Failed to load due");
    }
  }, [date]);

  const selectOrder = async (o: any) => {
    setOrder(o);
    setResults([]);
    setQ("");
    await refreshDue(o.id);
    setAmount("");
    amountRef.current?.focus();
  };

  const submit = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!order) return;
    setErr("");
    setMsg("");
    try {
      const p = await addPayment({
        order_id: order.id,
        amount: Number(amount || 0),
        date,
        method,
        reference,
        category,
        idempotencyKey: crypto.randomUUID(),
      });
      lastPaymentId.current = p?.id;
      await refreshDue(order.id);
      setAmount("");
      setMsg("Recorded");
      amountRef.current?.focus();
    } catch (e: any) {
      setErr(e?.message || "Failed to post");
    }
  };

  React.useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "z") {
        e.preventDefault();
        if (lastPaymentId.current) {
          voidPayment(lastPaymentId.current)
            .then(async () => {
              setMsg("Last payment voided");
              await refreshDue(order.id);
              lastPaymentId.current = null;
            })
            .catch((er: any) => setErr(er?.message || "Undo failed"));
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [order, refreshDue]);

  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const [mark, setMark] = React.useState(false);

  const doExport = async () => {
    if (!start || !end) return;
    setErr("");
    try {
      const blob = await exportPayments(start, end, { mark });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `cash-${start}-to-${end}.xlsx`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setErr(e?.message || "Export failed");
    }
  };

  return (
    <div className="stack">
      <div className="grid" style={{ gridTemplateColumns: "1fr 1fr 260px" }}>
        <Card className="stack" style={{ flex: 1 }}>
          <h2>Find Order</h2>
          <input
            className="input"
            placeholder="Search order..."
            value={q}
            onChange={(e) => setQ(e.target.value)}
          />
          {results.length > 0 && (
            <ul className="stack" style={{ maxHeight: 200, overflowY: "auto" }}>
              {results.map((r) => (
                <li key={r.id}>
                  <button
                    className="btn secondary"
                    style={{ width: "100%" }}
                    onClick={() => selectOrder(r)}
                  >
                    {r.code || r.id} - {r.customer_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
          {order && (
            <div className="stack">
              <div>
                <b>{order.code || order.id}</b> - {order.customer_name}
              </div>
              <div>Outstanding: RM {Number(due?.balance || 0).toFixed(2)}</div>
            </div>
          )}
        </Card>

        <Card className="stack" style={{ flex: 1 }}>
          <h2>Payment</h2>
          {order ? (
            <form className="stack" onSubmit={submit}>
              <input
                ref={amountRef}
                className="input"
                style={{ fontSize: 24 }}
                placeholder="Amount"
                value={amount}
                onChange={(e) => setAmount(e.target.value)}
              />
              <input
                className="input"
                placeholder="Method"
                value={method}
                onChange={(e) => setMethod(e.target.value)}
              />
              <input
                className="input"
                placeholder="Reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
              />
              <input
                className="input"
                placeholder="Category"
                value={category}
                onChange={(e) => setCategory(e.target.value)}
              />
              <div className="cluster">
                <input
                  className="input"
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                />
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() =>
                    setDate(new Date().toISOString().slice(0, 10))
                  }
                >
                  Today
                </button>
              </div>
              <button className="btn" type="submit" disabled={!amount}>
                Submit
              </button>
              {lastPaymentId.current && (
                <button 
                  className="btn secondary" 
                  onClick={() => window.open(`/_api/payments/${lastPaymentId.current}/receipt.pdf`, '_blank')}
                >
                  Last Payment Receipt
                </button>
              )}
            </form>
          ) : (
            <div>Select an order to record payment.</div>
          )}
          <div style={{ color: err ? "#ffb3b3" : "#9fffba" }}>{err || msg}</div>
        </Card>

        <Card className="stack" style={{ width: 260 }}>
          <h3>Export</h3>
          <div className="stack">
            <input
              className="input"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
            <input
              className="input"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
            <label className="cluster">
              <input
                type="checkbox"
                checked={mark}
                onChange={(e) => setMark(e.target.checked)}
              />
              Mark exported
            </label>
            <button
              type="button"
              className="btn"
              onClick={doExport}
              disabled={!start || !end}
            >
              Export
            </button>
            <Link
              href="/export"
              className="btn secondary"
              style={{ textAlign: "center" }}
            >
              View Export Runs
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}


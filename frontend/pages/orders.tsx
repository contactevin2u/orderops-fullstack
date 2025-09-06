import React from "react";
import ErrorBoundary from "@/components/ErrorBoundary";
import StatusBadge from "@/components/StatusBadge";
import UIDStatus from "@/components/UIDStatus";
import PageHeader from "@/components/PageHeader";
import Card from "@/components/Card";
import { Button } from "@/components/ui/button";
import { useOrders } from "@/hooks/useOrders";
import { useDrivers } from "@/hooks/useDrivers";
import { useToast } from "@/hooks/useToast";
import {
  addPayment,
  markReturned,
  cancelInstallment,
  markBuyback,
  markSuccess,
  assignOrderToDriver,
  invoicePrintUrl,
  orderDue,
  listDrivers,
} from "@/lib/api";
import Link from "next/link";

const PAGE_SIZE = 25;

export default function OperatorOrdersPage() {
  const [q, setQ] = React.useState("");
  const [status, setStatus] = React.useState("");
  const [event, setEvent] = React.useState("");
  const [outstanding, setOutstanding] = React.useState("");
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const [page, setPage] = React.useState(0);
  const [selected, setSelected] = React.useState<Set<number>>(new Set());
  const [active, setActive] = React.useState<number>(-1);

  const { success, error: showError } = useToast();
  
  const params = React.useMemo(() => ({
    q: q || undefined,
    status: status || undefined,
  }), [q, status]);

  const { data, error, isLoading, refetch } = useOrders(params);
  const { data: drivers } = useDrivers();

  React.useEffect(() => {
    const t = setTimeout(() => refetch(), 100);
    return () => clearTimeout(t);
  }, [params, refetch]);

  const items = data?.items || [];
  let filtered = items as any[];
  if (outstanding) {
    filtered = filtered.filter((o) =>
      outstanding === "yes" ? Number(o.balance || o.outstanding || 0) > 0 : Number(o.balance || o.outstanding || 0) <= 0
    );
  }
  if (start) filtered = filtered.filter((o) => o.updated_at && o.updated_at >= start);
  if (end) filtered = filtered.filter((o) => o.updated_at && o.updated_at <= `${end}T23:59:59`);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const current = filtered.slice(page * PAGE_SIZE, page * PAGE_SIZE + PAGE_SIZE);

  const recordPayment = React.useCallback(async (order: any) => {
    const amount = window.prompt("Amount?");
    if (!amount) return;
    const method = window.prompt("Method?") || undefined;
    const date = window.prompt("Date? (YYYY-MM-DD)") || undefined;
    try {
      await addPayment({
        order_id: order.id,
        amount: Number(amount),
        method,
        date,
        idempotencyKey: crypto.randomUUID(),
      });
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }, [refetch]);

  const markReturnOrCollect = React.useCallback(async (order: any) => {
    const collect = window.confirm("Collect item?");
    try {
      if (order.type === 'RENTAL' || !collect) {
        const d = await orderDue(order.id);
        if (d && Number(d?.outstanding || d?.balance || 0) > 0) {
          alert("Outstanding must be cleared before return");
          return;
        }
      }
    } catch (e: any) {
      alert(e?.message || "Failed");
      return;
    }
    try {
      await markReturned(order.id, undefined, { collect });
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }, [refetch]);

  const cancelInst = React.useCallback(async (order: any) => {
    try {
      await cancelInstallment(order.id, {});
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }, [refetch]);

  const buyback = React.useCallback(async (order: any) => {
    const amt = window.prompt("Buyback amount?");
    if (!amt) return;
    try {
      await markBuyback(order.id, Number(amt), {});
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }, [refetch]);

  React.useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target && (e.target as HTMLElement).tagName === "INPUT") return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActive((a) => Math.min(a + 1, current.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActive((a) => Math.max(a - 1, 0));
      } else if (e.key === "Enter" && active >= 0) {
        e.preventDefault();
        const order = current[active];
        if (order) window.open(`/orders/${order.id}`, "_blank");
      } else if (e.ctrlKey && active >= 0) {
        const order = current[active];
        if (!order) return;
        if (e.key.toLowerCase() === "p") {
          e.preventDefault();
          recordPayment(order);
        } else if (e.key.toLowerCase() === "r") {
          e.preventDefault();
          markReturnOrCollect(order);
        } else if (e.key.toLowerCase() === "b") {
          e.preventDefault();
          buyback(order);
        } else if (e.key.toLowerCase() === "m") {
          e.preventDefault();
          cancelInst(order);
        }
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [active, current, buyback, cancelInst, markReturnOrCollect, recordPayment]);

  function toggleSelect(id: number) {
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id);
      else n.add(id);
      return n;
    });
  }

  async function markDone(order: any) {
    try {
      await markSuccess(order.id);
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }

  async function assignDriver(order: any) {
    try {
      const drivers = await listDrivers();
      const choice = window.prompt(
        "Driver?\n" + drivers.map((d: any) => `${d.id}: ${d.name || ""}`).join("\n")
      );
      if (!choice) return;
      await assignOrderToDriver(order.id, choice);
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }

  function openInvoice(order: any) {
    window.open(invoicePrintUrl(order.id), "_blank", "noopener,noreferrer");
  }

  async function batchRecordPayment() {
    const amount = window.prompt("Amount?");
    if (!amount) return;
    const method = window.prompt("Method?") || undefined;
    const date = window.prompt("Date? (YYYY-MM-DD)") || undefined;
    for (const id of Array.from(selected)) {
      try {
        await addPayment({
          order_id: id,
          amount: Number(amount),
          method,
          date,
          idempotencyKey: crypto.randomUUID(),
        });
      } catch (e: any) {
        if (process.env.NODE_ENV === 'development') {
          console.error('Failed to create cash payment:', e);
        }
      }
    }
    refetch();
  }

  function batchExport() {
    const base = process.env.NEXT_PUBLIC_API_URL || "/_api";
    const ids = Array.from(selected).join(",");
    const url = `${base}/orders/export.xlsx?ids=${ids}`;
    if (typeof window !== "undefined") window.open(url, "_blank");
  }

  async function batchAssignDriver() {
    try {
      const drivers = await listDrivers();
      const choice = window.prompt(
        "Driver?\n" + drivers.map((d: any) => `${d.id}: ${d.name || ""}`).join("\n")
      );
      if (!choice) return;
      for (const id of Array.from(selected)) {
        try {
          await assignOrderToDriver(id, choice);
        } catch (e: any) {
          if (process.env.NODE_ENV === 'development') {
            console.error('Failed to assign order to driver:', e);
          }
        }
      }
      refetch();
    } catch (e: any) {
      alert(e?.message || "Failed");
    }
  }

  return (
      <div className="stack">
        <PageHeader title="Orders" />
        <Card className="stack">
          <div className="cluster">
            <input
              className="input"
              placeholder="Search"
              value={q}
              onChange={(e) => setQ(e.target.value)}
            />
          <select className="select" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All Status</option>
            <option>NEW</option>
            <option>ACTIVE</option>
            <option>COMPLETED</option>
            <option>RETURNED</option>
            <option>CANCELLED</option>
          </select>
          <select className="select" value={event} onChange={(e) => setEvent(e.target.value)}>
            <option value="">All Events</option>
            <option value="RETURN">RETURN</option>
            <option value="COLLECT">COLLECT</option>
            <option value="INSTALMENT_CANCEL">INSTALMENT_CANCEL</option>
            <option value="BUYBACK">BUYBACK</option>
          </select>
          <select className="select" value={outstanding} onChange={(e) => setOutstanding(e.target.value)}>
            <option value="">Outstanding?</option>
            <option value="yes">Yes</option>
            <option value="no">No</option>
          </select>
          <input type="date" className="input" value={start} onChange={(e)=>setStart(e.target.value)} />
          <input type="date" className="input" value={end} onChange={(e)=>setEnd(e.target.value)} />
        </div>

        {selected.size>0 && (
          <div className="cluster">
            <button className="btn secondary" onClick={batchRecordPayment}>Record Payment</button>
            <button className="btn secondary" onClick={batchExport}>Export</button>
            <button className="btn secondary" onClick={batchAssignDriver}>Assign Driver</button>
          </div>
        )}

        <p style={{fontSize:'0.875rem'}}>{isLoading?"Loading...":`${filtered.length} results`}</p>
        <ErrorBoundary fallback={<div style={{opacity:.7}}>orders.error</div>}>
          {error ? <ErrorThrower error={error} /> : (
            <OrdersTable
              items={current}
              selected={selected}
              toggleSelect={toggleSelect}
              active={active}
              setActive={setActive}
              actions={{
                recordPayment,
                markReturnOrCollect,
                cancelInst,
                buyback,
                markDone,
                assignDriver,
                openInvoice,
              }}
            />
          )}
        </ErrorBoundary>
        {totalPages>1 && (
          <div className="cluster" style={{justifyContent:'center'}}>
            <button className="btn secondary" disabled={page===0} onClick={()=>setPage(p=>p-1)}>Prev</button>
            <span style={{alignSelf:'center'}}>{page+1}/{totalPages}</span>
            <button className="btn secondary" disabled={page>=totalPages-1} onClick={()=>setPage(p=>p+1)}>Next</button>
          </div>
        )}
        </Card>
      </div>
  );
}

function ErrorThrower({ error }: { error: any }): JSX.Element | null {
  throw error;
  return null;
}

function OrdersTable({ items, selected, toggleSelect, active, setActive, actions }: { items: any[]; selected: Set<number>; toggleSelect: (id: number)=>void; active: number; setActive: (i:number)=>void; actions: any; }) {
  return (
    <div style={{ overflowX: "auto", marginTop: 12 }}>
      <table className="table">
        <thead>
          <tr>
            <th></th>
            <th>Code</th>
            <th>Customer</th>
            <th style={{ textAlign: 'right' }}>Amount</th>
            <th style={{ textAlign: 'right' }}>Outstanding</th>
            <th>Status</th>
            <th>Event</th>
            <th>UIDs</th>
            <th>Updated</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {items.map((o, idx) => (
            <tr key={o.id} style={active===idx?{background:'#eef'}:undefined} onClick={()=>setActive(idx)}>
              <td>
                <input type="checkbox" checked={selected.has(o.id)} onChange={()=>toggleSelect(o.id)} />
              </td>
              <td><Link href={`/orders/${o.id}`}>{o.code || o.id}</Link></td>
              <td>{o.customer_name || '-'}</td>
              <td style={{ textAlign: 'right' }}>RM {Number(o.total || 0).toFixed(2)}</td>
              <td style={{ textAlign: 'right' }}>RM {Number(o.balance || o.outstanding || 0).toFixed(2)}</td>
              <td><StatusBadge value={o.status} /></td>
              <td>{o.event || o.type || '-'}</td>
              <td><UIDStatus orderId={o.id} orderStatus={o.status} compact /></td>
              <td>{o.updated_at ? new Date(o.updated_at).toLocaleDateString() : '-'}</td>
              <td>
                <details>
                  <summary style={{cursor:'pointer'}}>...</summary>
                  <div className="stack" style={{minWidth:150}}>
                    <button className="btn secondary" onClick={()=>actions.recordPayment(o)}>Record Payment</button>
                    <button className="btn secondary" onClick={()=>actions.markReturnOrCollect(o)}>Return/Collect</button>
                    <button className="btn secondary" onClick={()=>actions.cancelInst(o)}>Cancel Instalment</button>
                    <button className="btn secondary" onClick={()=>actions.buyback(o)}>Buyback</button>
                    <button className="btn secondary" onClick={()=>actions.markDone(o)}>Mark Success</button>
                    <button className="btn secondary" onClick={()=>actions.assignDriver(o)}>Assign Driver</button>
                    <button className="btn secondary" onClick={()=>actions.openInvoice(o)}>Invoice PDF</button>
                  </div>
                </details>
              </td>
            </tr>
          ))}
          {items.length === 0 && (
            <tr>
              <td colSpan={10} style={{ opacity: 0.7 }}>No orders</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}


import Layout from "@/components/Layout";
import Link from "next/link";
import React from "react";
import { listOrders } from "@/utils/api";

export default function OrdersPage(){
  const [q,setQ] = React.useState("");
  const [status,setStatus] = React.useState("");
  const [type,setType] = React.useState("");
  const [items,setItems] = React.useState<any[]>([]);
  const [loading,setLoading] = React.useState(false);

  async function load(){
    setLoading(true);
    try{
      const r = await listOrders(q||undefined, status||undefined, type||undefined);
      setItems(r.items || []);
    }catch(e){ console.error(e); }
    setLoading(false);
  }

  React.useEffect(()=>{ load(); },[]);

  return (
    <Layout>
      <div className="card">
        <h2 style={{marginTop:0}}>Orders</h2>
        <div className="row">
          <div className="col"><input className="input" placeholder="Search..." value={q} onChange={e=>setQ(e.target.value)} /></div>
          <div className="col">
            <select className="select" value={status} onChange={e=>setStatus(e.target.value)}>
              <option value="">All Status</option>
              <option>NEW</option><option>ACTIVE</option><option>COMPLETED</option><option>RETURNED</option><option>CANCELLED</option>
            </select>
          </div>
          <div className="col">
            <select className="select" value={type} onChange={e=>setType(e.target.value)}>
              <option value="">All Types</option>
              <option>OUTRIGHT</option><option>INSTALLMENT</option><option>RENTAL</option>
            </select>
          </div>
          <div className="col" style={{display:"flex",alignItems:"center",gap:8}}>
            <button className="btn" onClick={load} disabled={loading}>{loading?"Loading...":"Search"}</button>
            <Link className="btn secondary" href="/orders/new">Create Manually</Link>
            <Link className="btn secondary" href="/parse">Create from Parse</Link>
          </div>
        </div>

        <div style={{overflowX:"auto", marginTop:12}}>
          <table className="table">
            <thead><tr><th>Code</th><th>Type</th><th>Status</th><th>Total</th><th>Paid</th><th>Balance</th></tr></thead>
            <tbody>
              {items.map((o:any)=>(
                <tr key={o.id}>
                  <td><Link href={`/orders/${o.id}`}>{o.code||o.id}</Link></td>
                  <td>{o.type}</td>
                  <td><span className="badge">{o.status}</span></td>
                  <td style={{textAlign:"right"}}>RM {Number(o.total||0).toFixed(2)}</td>
                  <td style={{textAlign:"right"}}>RM {Number(o.paid_amount||0).toFixed(2)}</td>
                  <td style={{textAlign:"right"}}>RM {Number(o.balance||0).toFixed(2)}</td>
                </tr>
              ))}
              {items.length===0 && <tr><td colSpan={6} style={{opacity:.7}}>No orders found</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}

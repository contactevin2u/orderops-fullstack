import Layout from "@/components/Layout";
import React from "react";
import { outstanding } from "@/utils/api";
import Link from "next/link";

export default function OutstandingPage(){
  const [tab,setTab] = React.useState<"INSTALLMENT"|"RENTAL">("INSTALLMENT");
  const [rows,setRows] = React.useState<any[]>([]);
  const [loading,setLoading] = React.useState(false);

  async function load(){
    setLoading(true);
    try{
      const r = await outstanding(tab);
      setRows(r.items || []);
    }catch(e){ console.error(e); }
    setLoading(false);
  }

  React.useEffect(()=>{ load(); },[tab]);

  return (
    <Layout>
      <div className="card">
        <h2 style={{marginTop:0}}>Outstanding</h2>
        <div className="nav">
          <button className="btn" onClick={()=>setTab("INSTALLMENT")} disabled={tab==="INSTALLMENT"}>Installments</button>
          <button className="btn secondary" onClick={()=>setTab("RENTAL")} disabled={tab==="RENTAL"}>Rentals</button>
          <button className="btn secondary" onClick={load} disabled={loading}>{loading?"Refreshing...":"Refresh"}</button>
        </div>
        <div style={{overflowX:"auto"}}>
          <table className="table">
            <thead><tr><th>Code</th><th>Customer</th><th>Type</th><th>Status</th><th>Balance</th></tr></thead>
            <tbody>
              {rows.map((r:any)=>(
                <tr key={r.id}>
                  <td><Link href={`/orders/${r.id}`}>{r.code||r.id}</Link></td>
                  <td>{r.customer?.name}</td>
                  <td>{r.type}</td>
                  <td><span className="badge">{r.status}</span></td>
                  <td style={{textAlign:"right"}}>RM {Number(r.balance||0).toFixed(2)}</td>
                </tr>
              ))}
              {rows.length===0 && <tr><td colSpan={5} style={{opacity:.7}}>No data</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </Layout>
  );
}

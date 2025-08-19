import Layout from "@/components/Layout";
import Link from "next/link";
import React from "react";
import { listOrders, ping } from "@/utils/api";

export default function HomePage(){
  const [ok, setOk] = React.useState<string>("checking...");
  const [recent, setRecent] = React.useState<any[]>([]);

  React.useEffect(()=>{
    ping().then(()=>setOk("OK")).catch(e=>setOk("ERROR: "+e.message));
    listOrders(undefined, undefined, undefined).then(r=>setRecent((r?.items||[]).slice(0,5))).catch(()=>{});
  },[]);

  return (
    <Layout>
      <div className="row">
        <div className="col">
          <div className="card">
            <h2 style={{marginTop:0}}>System</h2>
            <div className="kv">
              <div>Backend</div><div><b>{ok}</b></div>
            </div>
            <div className="hr" />
            <div className="row">
              <Link className="btn" href="/parse">Parse & Create</Link>
              <Link className="btn secondary" href="/orders">View Orders</Link>
              <Link className="btn secondary" href="/reports/outstanding">Outstanding</Link>
            </div>
          </div>
        </div>
        <div className="col">
          <div className="card">
            <h2 style={{marginTop:0}}>Recent Orders</h2>
            <div style={{overflowX:"auto"}}>
              <table className="table">
                <thead><tr><th>Code</th><th>Type</th><th>Status</th><th>Total</th><th>Paid</th><th>Balance</th></tr></thead>
                <tbody>
                  {recent.map((o:any)=>(
                    <tr key={o.id}>
                      <td><Link href={`/orders/${o.id}`}>{o.code||o.id}</Link></td>
                      <td>{o.type}</td>
                      <td><span className="badge">{o.status}</span></td>
                      <td style={{textAlign:"right"}}>RM {Number(o.total||0).toFixed(2)}</td>
                      <td style={{textAlign:"right"}}>RM {Number(o.paid_amount||0).toFixed(2)}</td>
                      <td style={{textAlign:"right"}}>RM {Number(o.balance||0).toFixed(2)}</td>
                    </tr>
                  ))}
                  {recent.length===0 && <tr><td colSpan={6} style={{opacity:.7}}>No data</td></tr>}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
}

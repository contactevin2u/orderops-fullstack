import Layout from "@/components/Layout";
import useSWR from "swr";
import { outstanding } from "@/utils/api";
import { useState } from "react";

function Block({ title, rows}:{ title:string; rows:any[] }){
  const total = rows.reduce((s,r)=> s + Number(r.balance||0), 0);
  return (
    <div className="card">
      <h3 style={{marginTop:0}}>{title} <small>({rows.length} orders)</small></h3>
      <table className="table">
        <thead><tr><th>Code</th><th>Customer</th><th>Total</th><th>Paid</th><th>Balance</th><th>Status</th></tr></thead>
        <tbody>
          {rows.map((r:any)=> (
            <tr key={r.id}>
              <td>{r.code}</td>
              <td>{r.customer?.name}</td>
              <td>RM {Number(r.total||0).toFixed(2)}</td>
              <td>RM {Number(r.paid_amount||0).toFixed(2)}</td>
              <td>RM {Number(r.balance||0).toFixed(2)}</td>
              <td>{r.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div style={{marginTop:8}}><b>Total Outstanding:</b> RM {total.toFixed(2)}</div>
    </div>
  );
}

export default function OutstandingPage(){
  const [tab, setTab] = useState<"INSTALLMENT"|"RENTAL">("INSTALLMENT");
  const { data: inst, error: e1 } = useSWR(tab==="INSTALLMENT" ? "outstanding-inst" : null, () => outstanding("INSTALLMENT"), { refreshInterval: 60000 });
  const { data: rent, error: e2 } = useSWR(tab==="RENTAL" ? "outstanding-rent" : null, () => outstanding("RENTAL"), { refreshInterval: 60000 });

  return (
    <Layout>
      <h2 style={{marginTop:0}}>Outstanding</h2>
      <div style={{display:'flex', gap:8, marginBottom:8}}>
        <button className={"btn " + (tab==="INSTALLMENT"?"":"ghost")} onClick={()=>setTab("INSTALLMENT")}>Installments</button>
        <button className={"btn " + (tab==="RENTAL"?"":"ghost")} onClick={()=>setTab("RENTAL")}>Rentals</button>
      </div>
      {e1 && <div style={{color:"var(--err)"}}>{String(e1)}</div>}
      {e2 && <div style={{color:"var(--err)"}}>{String(e2)}</div>}
      {tab==="INSTALLMENT" && inst && <Block title="Installment Orders" rows={inst} />}
      {tab==="RENTAL" && rent && <Block title="Rental Orders" rows={rent} />}
    </Layout>
  );
}

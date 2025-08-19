import Layout from "@/components/Layout";
import Link from "next/link";
import useSWR from "swr";
import { ping } from "@/utils/api";

export default function Home() {
  const { data, error } = useSWR("healthz", ping, { refreshInterval: 30000 });
  return (
    <Layout>
      <h2 style={{marginTop:0}}>Dashboard</h2>
      <div className="row">
        <div className="col card">
          <h3>Quick Actions</h3>
          <div style={{display:'flex',gap:8,flexWrap:'wrap'}}>
            <Link href="/parse" className="btn">Parse & Create</Link>
            <Link href="/orders" className="btn ghost">Orders</Link>
            <Link href="/reports/outstanding" className="btn ghost">Outstanding</Link>
          </div>
        </div>
        <div className="col card">
          <h3>API Health</h3>
          {error && <div style={{color:"var(--err)"}}>Backend unreachable: {String(error)}</div>}
          {!error && <div>Health: <span className="badge">{typeof data === "string" ? data : "OK"}</span></div>}
          <small>Polling every 30s</small>
        </div>
      </div>
    </Layout>
  );
}

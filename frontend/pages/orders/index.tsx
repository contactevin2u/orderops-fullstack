import Layout from "@/components/Layout";
import Link from "next/link";
import useSWR from "swr";
import { listOrders } from "@/utils/api";

export default function OrdersPage() {
  const { data, error, isLoading, mutate } = useSWR("orders", listOrders, { refreshInterval: 30000 });
  return (
    <Layout>
      <h2 style={{marginTop:0}}>Orders</h2>
      {error && <div style={{color:"var(--err)"}}>{String(error)}</div>}
      {isLoading && <div>Loading...</div>}
      {data && (
        <table className="table">
          <thead><tr><th>Code</th><th>Customer</th><th>Type</th><th>Status</th><th>Total</th><th>Paid</th><th>Balance</th><th></th></tr></thead>
          <tbody>
          {data.map((o:any)=> (
            <tr key={o.id}>
              <td><span className="badge">{o.code}</span></td>
              <td>{o.customer?.name}</td>
              <td>{o.type}</td>
              <td>{o.status}</td>
              <td>RM {Number(o.total||0).toFixed(2)}</td>
              <td>RM {Number(o.paid_amount||0).toFixed(2)}</td>
              <td>RM {Number(o.balance||0).toFixed(2)}</td>
              <td><Link href={`/orders/${o.id}`} className="btn">Open</Link></td>
            </tr>
          ))}
          </tbody>
        </table>
      )}
    </Layout>
  );
}

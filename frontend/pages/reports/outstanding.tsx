import Layout from "@/components/Layout";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import React from "react";
import { outstanding } from "@/utils/api";
import Link from "next/link";

export default function OutstandingPage() {
  const [tab, setTab] = React.useState<"INSTALLMENT" | "RENTAL">(
    "INSTALLMENT"
  );
  const [rows, setRows] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const r = await outstanding(tab);
      setRows(r.items || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [tab]);

  React.useEffect(() => {
    load();
  }, [load]);
  return (
    <Layout>
      <div className="container stack" style={{ maxWidth: '64rem' }}>
        <Card>
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>Outstanding</h2>
          <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
            <Button onClick={() => setTab('INSTALLMENT')} disabled={tab === 'INSTALLMENT'}>
              Installments
            </Button>
            <Button
              variant="secondary"
              onClick={() => setTab('RENTAL')}
              disabled={tab === 'RENTAL'}
            >
              Rentals
            </Button>
            <Button variant="secondary" onClick={load} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  <th>Code</th>
                  <th>Customer</th>
                  <th>Type</th>
                  <th>Status</th>
                  <th>Balance</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((r: any) => (
                  <tr key={r.id}>
                    <td>
                      <Link href={`/orders/${r.id}`}>{r.code || r.id}</Link>
                    </td>
                    <td>{r.customer?.name}</td>
                    <td>{r.type}</td>
                    <td>
                      <span className="badge">{r.status}</span>
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      RM {Number(r.balance || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={5} style={{ opacity: 0.7 }}>
                      No data
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </Layout>
  );
}


import Layout from "@/components/Layout";
import Card from "@/components/Card";
import Button from "@/components/ui/Button";
import React from "react";
import { outstanding } from "@/utils/api";
import Link from "next/link";

export default function OutstandingPage() {
  const [type, setType] = React.useState<string>("ALL");
  const [asOf, setAsOf] = React.useState<string>(() =>
    new Date().toISOString().slice(0, 10)
  );
  const [rows, setRows] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [sort, setSort] = React.useState<{key: string; asc: boolean}>({key: '', asc: true});

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const r = await outstanding(type, asOf);
      setRows(r.items || []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, [type, asOf]);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <Layout>
      <div className="container stack" style={{ maxWidth: '64rem' }}>
        <Card>
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>Outstanding</h2>
          <div
            style={{
              display: 'flex',
              gap: 8,
              marginBottom: 16,
              flexWrap: 'wrap',
              alignItems: 'center',
            }}
          >
            <label>
              Type:
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                style={{ marginLeft: 4 }}
              >
                <option value="ALL">All</option>
                <option value="OUTRIGHT">Outright</option>
                <option value="INSTALLMENT">Installment</option>
                <option value="RENTAL">Rental</option>
                <option value="MIXED">Mixed</option>
              </select>
            </label>
            <label>
              As of:
              <input
                type="date"
                value={asOf}
                onChange={(e) => setAsOf(e.target.value)}
                style={{ marginLeft: 4 }}
              />
            </label>
            <Button variant="secondary" onClick={load} disabled={loading}>
              {loading ? 'Refreshing...' : 'Refresh'}
            </Button>
          </div>
          <div style={{ overflowX: 'auto' }}>
            <table className="table">
              <thead>
                <tr>
                  {['code','customer','type','status','expected','paid','fees','balance'].map((k) => (
                    <th
                      key={k}
                      onClick={() =>
                        setSort((s) => ({ key: k, asc: s.key === k ? !s.asc : true }))
                      }
                      style={{ cursor: 'pointer' }}
                    >
                      {k.charAt(0).toUpperCase() + k.slice(1)}
                      {sort.key === k ? (sort.asc ? ' ▲' : ' ▼') : ''}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows
                  .slice()
                  .sort((a: any, b: any) => {
                    if (!sort.key) return 0;
                    const av = a[sort.key];
                    const bv = b[sort.key];
                    if (av === bv) return 0;
                    return av > bv ? (sort.asc ? 1 : -1) : sort.asc ? -1 : 1;
                  })
                  .map((r: any) => (
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
                      RM {Number(r.expected || 0).toFixed(2)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      RM {Number(r.paid || 0).toFixed(2)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      RM {Number(r.fees || 0).toFixed(2)}
                    </td>
                    <td style={{ textAlign: 'right' }}>
                      RM {Number(r.balance || 0).toFixed(2)}
                    </td>
                  </tr>
                ))}
                {rows.length === 0 && (
                  <tr>
                    <td colSpan={8} style={{ opacity: 0.7 }}>
                      No data
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <div style={{marginTop:8}}>
            <Button
              variant="secondary"
              onClick={() => {
                const header = ['Code','Customer','Type','Status','Expected','Paid','Fees','Balance'];
                const csv = [header.join(',')]
                  .concat(
                    rows.map((r:any)=>([
                      r.code||r.id,
                      r.customer?.name||'',
                      r.type,
                      r.status,
                      r.expected,
                      r.paid,
                      r.fees,
                      r.balance,
                    ].join(',')))
                  ).join('\n');
                const blob = new Blob([csv], {type:'text/csv'});
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `outstanding_${asOf}.csv`;
                a.click();
                URL.revokeObjectURL(url);
              }}
            >
              Export CSV
            </Button>
          </div>
        </Card>
      </div>
    </Layout>
  );
}


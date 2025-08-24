import Layout from "@/components/Layout";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import React from "react";
import { listTrips, notifyTrip } from "@/utils/api";

export default function DispatcherPage() {
  const [trips, setTrips] = React.useState<any[]>([]);
  const [loading, setLoading] = React.useState(false);

  const load = React.useCallback(async () => {
    setLoading(true);
    try {
      const r = await listTrips();
      setTrips(Array.isArray(r) ? r : []);
    } catch (e) {
      console.error(e);
    }
    setLoading(false);
  }, []);

  React.useEffect(() => {
    load();
  }, [load]);

  return (
    <Layout>
      <div className="container stack" style={{ maxWidth: '64rem' }}>
        <Card>
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>Dispatcher</h2>
          <Button variant="secondary" onClick={load} disabled={loading}>
            {loading ? 'Refreshing...' : 'Refresh'}
          </Button>
          <div style={{ overflowX: 'auto', marginTop: 16 }}>
            <table className="table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Order</th>
                  <th>Driver</th>
                  <th>Status</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {trips.map((t: any) => (
                  <tr key={t.id}>
                    <td>{t.id}</td>
                    <td>{t.order_id}</td>
                    <td>{t.driver_id}</td>
                    <td>{t.status}</td>
                    <td>
                      <Button
                        variant="secondary"
                        onClick={() => notifyTrip(t.id).catch(console.error)}
                      >
                        Resend
                      </Button>
                    </td>
                  </tr>
                ))}
                {trips.length === 0 && (
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

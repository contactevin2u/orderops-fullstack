import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/StatusBadge';
import {
  listOrders,
  listDrivers,
  assignOrderToDriver,
  createDriver,
} from '@/utils/api';

export default function AdminPanel() {
  const [section, setSection] = React.useState<'orders' | 'drivers'>('orders');
  const [orders, setOrders] = React.useState<any[]>([]);
  const [drivers, setDrivers] = React.useState<any[]>([]);

  const [orderId, setOrderId] = React.useState('');
  const [driverId, setDriverId] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState('');
  const [err, setErr] = React.useState('');
  const [orderTab, setOrderTab] = React.useState<'unassigned' | 'assigned'>('unassigned');

  const [email, setEmail] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [name, setName] = React.useState('');
  const [drvMsg, setDrvMsg] = React.useState('');
  const [drvErr, setDrvErr] = React.useState('');
  const [creating, setCreating] = React.useState(false);

  React.useEffect(() => {
    listOrders(undefined, undefined, undefined, 50)
      .then((res) => setOrders(res.items))
      .catch(() => {});
    listDrivers().then(setDrivers).catch(() => {});
  }, []);

  async function onAssign() {
    if (!orderId || !driverId) return;
    setBusy(true);
    setErr('');
    setMsg('');
    try {
      await assignOrderToDriver(orderId, driverId);
      setMsg('Order assigned');
      setOrderId('');
      setDriverId('');
      try {
        const res = await listOrders(undefined, undefined, undefined, 50);
        setOrders(res.items);
      } catch {}
    } catch (e: any) {
      setErr(e?.message || 'Assignment failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCreateDriver() {
    if (!email || !password) return;
    setCreating(true);
    setDrvErr('');
    setDrvMsg('');
    try {
      await createDriver({ email, password, name });
      setDrvMsg('Driver created');
      setEmail('');
      setPassword('');
      setName('');
      const ds = await listDrivers();
      setDrivers(ds);
    } catch (e: any) {
      setDrvErr(e?.message || 'Creation failed');
    } finally {
      setCreating(false);
    }
  }

  const unassigned = orders.filter((o: any) => !(o.trip && o.trip.driver_id));
  const assigned = orders.filter((o: any) => o.trip && o.trip.driver_id);
  const current = orderTab === 'unassigned' ? unassigned : assigned;

  return (
    <div className="stack container" style={{ maxWidth: '48rem' }}>
      <div style={{ display: 'flex', gap: 8 }}>
        <button
          className={`btn ${section === 'orders' ? '' : 'secondary'}`}
          onClick={() => setSection('orders')}
        >
          Assignments
        </button>
        <button
          className={`btn ${section === 'drivers' ? '' : 'secondary'}`}
          onClick={() => setSection('drivers')}
        >
          Drivers
        </button>
      </div>

      {section === 'orders' && (
        <>
          <Card>
            <div className="stack">
              <label>
                Order
                <select value={orderId} onChange={(e) => setOrderId(e.target.value)}>
                  <option value="">Select order</option>
                  {orders.map((o) => (
                    <option key={o.id} value={o.id}>
                      {o.code || `Order ${o.id}`}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                Driver
                <select value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                  <option value="">Select driver</option>
                  {drivers.map((d: any) => (
                    <option key={d.id || d.uid} value={d.id || d.uid}>
                      {d.name || d.id || d.uid}
                    </option>
                  ))}
                </select>
              </label>
              <Button onClick={onAssign} disabled={busy || !orderId || !driverId}>
                Assign
              </Button>
              {err && <p style={{ color: '#ff4d4f', fontSize: '0.875rem' }}>{err}</p>}
              {msg && <p style={{ color: '#16a34a', fontSize: '0.875rem' }}>{msg}</p>}
            </div>
          </Card>

          <div className="stack" style={{ marginTop: '1rem' }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                className={`btn ${orderTab === 'unassigned' ? '' : 'secondary'}`}
                onClick={() => setOrderTab('unassigned')}
              >
                Unassigned Orders
              </button>
              <button
                className={`btn ${orderTab === 'assigned' ? '' : 'secondary'}`}
                onClick={() => setOrderTab('assigned')}
              >
                Assigned Orders
              </button>
            </div>
            <Card>
              <table className="table">
                <thead>
                  <tr>
                    <th>Order</th>
                    <th>Status</th>
                    {orderTab === 'assigned' && <th>Driver</th>}
                  </tr>
                </thead>
                <tbody>
                  {current.map((o: any) => (
                    <tr key={o.id}>
                      <td>{o.code || `Order ${o.id}`}</td>
                      <td>
                        <StatusBadge value={(o.trip && o.trip.status) || o.status} />
                      </td>
                      {orderTab === 'assigned' && (
                        <td>{o.trip?.driver_name || o.driver?.name || o.driver_id || '-'}</td>
                      )}
                    </tr>
                  ))}
                  {current.length === 0 && (
                    <tr>
                      <td colSpan={orderTab === 'assigned' ? 3 : 2} style={{ opacity: 0.7 }}>
                        No orders
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}

      {section === 'drivers' && (
        <>
          <Card>
            <div className="stack">
              <label>
                Email
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </label>
              <label>
                Password
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </label>
              <label>
                Name
                <input value={name} onChange={(e) => setName(e.target.value)} />
              </label>
              <Button onClick={onCreateDriver} disabled={creating || !email || !password}>
                Create
              </Button>
              {drvErr && <p style={{ color: '#ff4d4f', fontSize: '0.875rem' }}>{drvErr}</p>}
              {drvMsg && <p style={{ color: '#16a34a', fontSize: '0.875rem' }}>{drvMsg}</p>}
            </div>
          </Card>

          <div style={{ marginTop: '1rem' }}>
            <Card>
              <table className="table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>ID</th>
                  </tr>
                </thead>
                <tbody>
                  {drivers.map((d: any) => (
                    <tr key={d.id}>
                      <td>{d.name || '-'}</td>
                      <td>{d.id}</td>
                    </tr>
                  ))}
                  {drivers.length === 0 && (
                    <tr>
                      <td colSpan={2} style={{ opacity: 0.7 }}>
                        No drivers
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

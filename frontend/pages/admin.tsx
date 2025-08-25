import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/Button';
import StatusBadge from '@/components/StatusBadge';
import {
  listOrders,
  listDrivers,
  assignOrderToDriver,
  createDriver,
  listDriverCommissions,
  createRoute,
  listRoutes,
  addOrdersToRoute,
} from '@/utils/api';

export default function AdminPanel() {
  const [section, setSection] = React.useState<'orders' | 'drivers'>('orders');
  const [orders, setOrders] = React.useState<any[]>([]);
  const [drivers, setDrivers] = React.useState<any[]>([]);
  const [commissions, setCommissions] = React.useState<Record<number, number>>({});

  const [orderId, setOrderId] = React.useState('');
  const [driverId, setDriverId] = React.useState('');
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState('');
  const [err, setErr] = React.useState('');
  const [routes, setRoutes] = React.useState<any[]>([]);
  const [routeDate, setRouteDate] = React.useState<string>(
    new Date().toISOString().slice(0, 10)
  );
  const [routeDriverId, setRouteDriverId] = React.useState<string>('');
  const [selected, setSelected] = React.useState<Set<number>>(new Set());

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
    listDrivers()
      .then((ds) => {
        setDrivers(ds);
        const month = new Date().toISOString().slice(0, 7);
        Promise.all(
          ds.map((d: any) =>
            listDriverCommissions(d.id)
              .then((arr) => {
                const entry = arr.find((it: any) => it.month === month);
                return [d.id, entry ? entry.total : 0];
              })
              .catch(() => [d.id, 0])
          )
        ).then((pairs) => {
          setCommissions(Object.fromEntries(pairs as any));
        });
      })
      .catch(() => {});
  }, []);

  React.useEffect(() => {
    listRoutes(routeDate).then(setRoutes).catch(() => {});
  }, [routeDate]);

  async function onAssign() {
    if (!orderId || !driverId) return;
    setBusy(true);
    setErr('');
    setMsg('');
    try {
      const order = orders.find((o: any) => String(o.id) === String(orderId));
      const driver = drivers.find(
        (d: any) => String(d.id || d.uid) === String(driverId)
      );
      const currentDriverName =
        order?.trip?.driver_name ||
        (order?.trip?.driver_id ? `ID ${order.trip.driver_id}` : null);
      const newDriverName = driver?.name || driverId;
      if (order?.trip?.driver_id) {
        const ok = window.confirm(
          `This order is currently assigned to ${currentDriverName}. Reassign to ${newDriverName}?`
        );
        if (!ok) {
          setBusy(false);
          return;
        }
      }
      await assignOrderToDriver(orderId, driverId);
      setMsg('Order assigned');
      const res = await listOrders(undefined, undefined, undefined, 50);
      setOrders(res.items);
    } catch (e: any) {
      setErr(e?.message || 'Assignment failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCreateRoute() {
    if (!routeDriverId) return;
    await createRoute({
      driver_id: Number(routeDriverId),
      route_date: routeDate,
    });
    setRoutes(await listRoutes(routeDate));
  }

  function toggleSelected(id: number) {
    setSelected((prev) => {
      const copy = new Set(prev);
      if (copy.has(id)) copy.delete(id);
      else copy.add(id);
      return copy;
    });
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

  const unassigned = orders.filter(
    (o: any) => !(o.trip && o.trip.driver_id)
  );
  const onHold = orders.filter(
    (o: any) => o.trip?.status === 'ON_HOLD'
  );

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
          {/* Routes Section */}
          <Card>
            <div className="cluster">
              <input type="date" value={routeDate} onChange={e => setRouteDate(e.target.value)} />
              <select value={routeDriverId} onChange={e => setRouteDriverId(e.target.value)}>
                <option value="">Driver</option>
                {drivers.map((d:any)=><option key={d.id} value={d.id}>{d.name||d.id}</option>)}
              </select>
              <Button onClick={onCreateRoute} disabled={!routeDriverId}>Create Route</Button>
            </div>
          </Card>

          {routes.map(r => (
            <Card key={r.id}>
              <div className="cluster" style={{justifyContent:"space-between"}}>
                <div>Route #{r.id} • {r.route_date} • Driver {r.driver_id}</div>
                <Button
                  onClick={async () => {
                    await addOrdersToRoute(r.id, Array.from(selected));
                    setSelected(new Set());
                    const res = await listOrders(undefined, undefined, undefined, 50);
                    setOrders(res.items);
                  }}
                  disabled={selected.size===0}
                >
                  Add Selected Orders
                </Button>
              </div>
            </Card>
          ))}

          {/* Assign Panel */}
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

          {/* Orders lists */}
          <div className="stack" style={{ marginTop: '1rem' }}>
            <Card>
              <table className="table">
                <thead>
                  <tr>
                    <th></th>
                    <th>Order</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {unassigned.map((o: any) => (
                    <tr key={o.id}>
                      <td>
                        <input
                          type="checkbox"
                          checked={selected.has(o.id)}
                          onChange={() => toggleSelected(o.id)}
                        />
                      </td>
                      <td>{o.code || `Order ${o.id}`}</td>
                      <td>
                        <StatusBadge value={(o.trip && o.trip.status) || o.status} />
                      </td>
                    </tr>
                  ))}
                  {unassigned.length === 0 && (
                    <tr>
                      <td colSpan={3} style={{ opacity: 0.7 }}>
                        No orders
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </Card>

            {onHold.length > 0 && (
              <Card>
                <div style={{ fontWeight: 'bold', marginBottom: 4 }}>
                  On Hold ({onHold.length})
                </div>
                <table className="table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Order</th>
                    </tr>
                  </thead>
                  <tbody>
                    {onHold.map((o: any) => (
                      <tr key={o.id}>
                        <td>
                          <input
                            type="checkbox"
                            checked={selected.has(o.id)}
                            onChange={() => toggleSelected(o.id)}
                          />
                        </td>
                        <td>{o.code || `Order ${o.id}`}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Card>
            )}
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
                    <th>Commission (month)</th>
                  </tr>
                </thead>
                <tbody>
                  {drivers.map((d: any) => (
                    <tr key={d.id}>
                      <td>{d.name || '-'}</td>
                      <td>{d.id}</td>
                      <td>{(commissions[d.id] ?? 0).toFixed(2)}</td>
                    </tr>
                  ))}
                  {drivers.length === 0 && (
                    <tr>
                      <td colSpan={3} style={{ opacity: 0.7 }}>
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

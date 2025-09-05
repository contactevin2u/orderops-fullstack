import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { fetchUnassigned, Order } from '@/lib/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';
import AdminLayout from '@/components/Layout/AdminLayout';

const AssignToRouteModal = dynamic(() => import('@/components/admin/AssignToRouteModal'));

export default function AdminAssignPage() {
  const router = useRouter();
  const dateParam = typeof router.query.date === 'string' ? router.query.date : '';
  const today = new Date().toLocaleDateString('en-CA');
  const date = dateParam || today;

  React.useEffect(() => {
    if (!dateParam) {
      router.replace({ pathname: router.pathname, query: { date } });
    }
  }, [dateParam, date, router]);

  const ordersQuery = useQuery({
    queryKey: ['unassigned', date],
    queryFn: () => fetchUnassigned(date),
  });
  const orders = React.useMemo(() => ordersQuery.data || [], [ordersQuery.data]);

  const counts = React.useMemo(() => {
    let noDate = 0;
    let overdue = 0;
    orders.forEach((o) => {
      const badges = getOrderBadges(o, date);
      if (badges.includes('No date')) noDate += 1;
      if (badges.some((b) => b.startsWith('Overdue'))) overdue += 1;
    });
    return { noDate, overdue };
  }, [orders, date]);

  const [selected, setSelected] = React.useState<Set<string>>(new Set());
  const [showCompleted, setShowCompleted] = React.useState(false);
  const [showModal, setShowModal] = React.useState(false);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const copy = new Set(prev);
      if (copy.has(id)) copy.delete(id);
      else copy.add(id);
      return copy;
    });
  };

  const visible = orders.filter(
    (o) => showCompleted || (o.status !== 'SUCCESS' && o.status !== 'DELIVERED')
  );
  const allSelected = visible.length > 0 && visible.every((o) => selected.has(o.id));
  const someSelected = visible.some((o) => selected.has(o.id));
  const selectAllRef = React.useRef<HTMLInputElement>(null);
  React.useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = someSelected && !allSelected;
    }
  }, [someSelected, allSelected]);
  const toggleAll = (checked: boolean) => {
    setSelected((prev) => {
      const next = new Set(prev);
      visible.forEach((o) => {
        if (checked) next.add(o.id);
        else next.delete(o.id);
      });
      return next;
    });
  };

  return (
    <div className="main">
      <div className="container">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-6)' }}>Assign Orders</h1>
        <header className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="cluster" style={{ marginBottom: 'var(--space-4)' }}>
            <label className="cluster" style={{ fontSize: '0.875rem' }}>
              <span style={{ fontWeight: 500 }}>Date:</span>
              <input
                type="date"
                value={date}
                onChange={(e) => router.push({ pathname: '/admin/assign', query: { date: e.target.value } })}
                className="input"
                style={{ fontSize: '0.875rem' }}
              />
            </label>
            <label className="cluster" style={{ fontSize: '0.875rem' }}>
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={(e) => setShowCompleted(e.target.checked)}
              />
              <span>Show completed</span>
            </label>
          </div>
          <div className="cluster" style={{ fontSize: '0.875rem' }}>
            <span className="cluster">
              <span style={{ fontWeight: 500, color: '#ea580c' }}>{orders.length}</span>
              <span>Unassigned</span>
            </span>
            <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
              (No date: {counts.noDate}, Overdue: {counts.overdue})
            </span>
            <span className="cluster">
              <span style={{ fontWeight: 500, color: '#2563eb' }}>{selected.size}</span>
              <span>Selected</span>
            </span>
          </div>
        </header>
        <div className="card" style={{ overflow: 'hidden' }}>
          <table className="table">
          <caption className="sr-only">Unassigned orders</caption>
          <thead>
            <tr>
              <th>
                <input
                  ref={selectAllRef}
                  type="checkbox"
                  aria-label="Select all"
                  checked={allSelected}
                  onChange={(e) => toggleAll(e.target.checked)}
                />
              </th>
              <th>Order#</th>
              <th>Delivery Date</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {ordersQuery.isLoading && (
              <tr>
                <td colSpan={4} role="status">
                  Loading...
                </td>
              </tr>
            )}
            {ordersQuery.isError && (
              <tr>
                <td colSpan={4} role="alert">
                  Failed to load
                </td>
              </tr>
            )}
            {!ordersQuery.isLoading &&
              visible.map((o: Order) => (
                <tr key={o.id}>
                  <td>
                    <input
                      type="checkbox"
                      aria-label={`Select order ${o.orderNo}`}
                      checked={selected.has(o.id)}
                      onChange={() => toggle(o.id)}
                    />
                  </td>
                  <td>{o.orderNo}</td>
                  <td>
                    {o.deliveryDate}{' '}
                    {getOrderBadges(o, date).map((b) => (
                      <span key={b} className="badge" style={{
                        marginLeft: 'var(--space-2)',
                        background: '#fef2f2',
                        color: '#dc2626',
                        fontSize: '0.75rem'
                      }}>
                        {b}
                      </span>
                    ))}
                  </td>
                  <td>{o.status}</td>
                </tr>
              ))}
            {!ordersQuery.isLoading && visible.length === 0 && (
              <tr>
                <td colSpan={4} style={{ textAlign: 'center', padding: 'var(--space-8) 0', opacity: 0.7 }}>
                  No orders found
                </td>
              </tr>
            )}
          </tbody>
        </table>
        </div>
        <div style={{
          position: 'sticky',
          bottom: 0,
          background: 'var(--color-surface)',
          padding: 'var(--space-4)',
          marginTop: 'var(--space-4)',
          borderTop: '1px solid var(--color-border)',
          borderRadius: 'var(--radius-4)'
        }}>
          <div className="cluster">
            <button
              className="btn secondary"
              onClick={() => setSelected(new Set())}
              disabled={selected.size === 0}
            >
              Clear Selection
            </button>
            <button 
              className="btn" 
              onClick={() => setShowModal(true)} 
              disabled={selected.size === 0}
            >
              Assign to Route
            </button>
          </div>
        </div>
        {showModal && (
          <AssignToRouteModal
            orderIds={[...selected]}
            date={date}
            onClose={() => {
              setShowModal(false);
              setSelected(new Set());
            }}
          />
        )}
      </div>
    </div>
  );
}

(AdminAssignPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

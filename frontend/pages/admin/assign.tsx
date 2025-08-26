import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { fetchUnassigned, Order } from '@/utils/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';
import AdminLayout from '@/components/admin/AdminLayout';

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
  const orders = ordersQuery.data || [];

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
    <div style={{ padding: 16 }}>
      <h1>Assign Orders</h1>
      <header style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span>Date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => router.push({ pathname: '/admin/assign', query: { date: e.target.value } })}
          />
        </label>
        <label>
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
          />{' '}
          Show completed
        </label>
        <span aria-live="polite">
          Unassigned: {orders.length} (No date: {counts.noDate} Overdue: {counts.overdue})
        </span>
        <span aria-live="polite">Selected: {selected.size}</span>
      </header>
      <table className="table" style={{ marginTop: 16 }}>
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
                    <span key={b} style={{ marginLeft: 4, fontSize: '0.8em', color: '#c00' }}>
                      {b}
                    </span>
                  ))}
                </td>
                <td>{o.status}</td>
              </tr>
            ))}
          {!ordersQuery.isLoading && visible.length === 0 && (
            <tr>
              <td colSpan={4} style={{ opacity: 0.6 }}>
                No orders
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div
        style={{
          position: 'sticky',
          bottom: 0,
          background: '#fff',
          paddingTop: 8,
          paddingBottom: 8,
          marginTop: 8,
          display: 'flex',
          gap: 8,
          borderTop: '1px solid #eee',
        }}
      >
        <button
          className="btn secondary"
          onClick={() => setSelected(new Set())}
          disabled={selected.size === 0}
        >
          Clear
        </button>
        <button className="btn" onClick={() => setShowModal(true)} disabled={selected.size === 0}>
          Assign to route
        </button>
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
  );
}

(AdminAssignPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

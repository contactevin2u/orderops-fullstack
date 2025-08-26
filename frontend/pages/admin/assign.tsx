import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { fetchUnassigned, Order } from '@/utils/apiAdapter';

const AssignToRouteModal = dynamic(() => import('@/components/admin/AssignToRouteModal'));

export default function AdminAssignPage() {
  const router = useRouter();
  const dateParam = typeof router.query.date === 'string' ? router.query.date : '';
  const today = new Date().toISOString().slice(0, 10);
  const date = dateParam || today;

  React.useEffect(() => {
    if (!dateParam) {
      router.replace({ pathname: router.pathname, query: { date } });
    }
  }, [dateParam, date, router]);

  const { data: orders } = useQuery(['unassigned', date], () => fetchUnassigned(date));

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

  const visible = (orders || []).filter(
    (o) => showCompleted || (o.status !== 'SUCCESS' && o.status !== 'DELIVERED')
  );

  return (
    <div style={{ padding: 16 }}>
      <header style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="date"
          value={date}
          onChange={(e) => router.push({ pathname: '/admin/assign', query: { date: e.target.value } })}
        />
        <label>
          <input
            type="checkbox"
            checked={showCompleted}
            onChange={(e) => setShowCompleted(e.target.checked)}
          />{' '}
          Show completed
        </label>
      </header>
      <table className="table" style={{ marginTop: 16 }}>
        <thead>
          <tr>
            <th></th>
            <th>Order#</th>
            <th>Delivery Date</th>
            <th>Status</th>
          </tr>
        </thead>
        <tbody>
          {visible.map((o: Order) => (
            <tr key={o.id}>
              <td>
                <input
                  type="checkbox"
                  checked={selected.has(o.id)}
                  onChange={() => toggle(o.id)}
                />
              </td>
              <td>{o.orderNo}</td>
              <td>{o.deliveryDate}</td>
              <td>{o.status}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected.size > 0 && (
        <button style={{ marginTop: 8 }} onClick={() => setShowModal(true)}>
          Assign to route
        </button>
      )}
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

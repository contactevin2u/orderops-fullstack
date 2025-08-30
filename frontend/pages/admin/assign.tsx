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
    <div className="container">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Assign Orders</h1>
      <header className="bg-white p-4 rounded-lg border border-gray-200 mb-6">
        <div className="flex flex-wrap items-center gap-4 mb-4">
          <label className="flex items-center gap-2 text-sm">
            <span className="font-medium text-gray-700">Date:</span>
            <input
              type="date"
              value={date}
              onChange={(e) => router.push({ pathname: '/admin/assign', query: { date: e.target.value } })}
              className="input text-sm"
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={showCompleted}
              onChange={(e) => setShowCompleted(e.target.checked)}
              className="rounded border-gray-300 text-primary focus:ring-primary"
            />
            <span className="text-gray-700">Show completed</span>
          </label>
        </div>
        <div className="flex flex-wrap items-center gap-4 text-sm text-gray-600">
          <span className="flex items-center gap-1">
            <span className="font-medium text-orange-600">{orders.length}</span> Unassigned
          </span>
          <span className="text-xs text-gray-500">
            (No date: {counts.noDate}, Overdue: {counts.overdue})
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-blue-600">{selected.size}</span> Selected
          </span>
        </div>
      </header>
      <div className="bg-white rounded-lg border border-gray-200 overflow-hidden">
        <table className="table w-full">
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
                    <span key={b} className="ml-2 text-xs text-red-600 bg-red-50 px-2 py-1 rounded">
                      {b}
                    </span>
                  ))}
                </td>
                <td>{o.status}</td>
              </tr>
            ))}
          {!ordersQuery.isLoading && visible.length === 0 && (
            <tr>
              <td colSpan={4} className="text-center py-8 text-gray-500">
                No orders found
              </td>
            </tr>
          )}
        </tbody>
      </table>
      </div>
      <div className="sticky bottom-0 bg-white p-4 mt-4 border-t border-gray-200 flex gap-3 rounded-lg">
        <button
          className="btn btn-secondary"
          onClick={() => setSelected(new Set())}
          disabled={selected.size === 0}
        >
          Clear Selection
        </button>
        <button 
          className="btn btn-primary" 
          onClick={() => setShowModal(true)} 
          disabled={selected.size === 0}
        >
          Assign to Route
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

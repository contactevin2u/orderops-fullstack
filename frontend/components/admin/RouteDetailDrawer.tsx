import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Route, Order } from '@/utils/apiAdapter';
import {
  fetchUnassigned,
  assignOrdersToRoute,
  removeOrdersFromRoute,
  fetchRouteOrders,
} from '@/utils/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';

interface Props {
  route: Route;
  onClose: () => void;
}

export default function RouteDetailDrawer({ route, onClose }: Props) {
  const qc = useQueryClient();
  const unassignedQuery = useQuery({
    queryKey: ['unassigned', route.date],
    queryFn: () => fetchUnassigned(route.date),
  });
  const unassigned = unassignedQuery.data || [];

  const assignedQuery = useQuery({
    queryKey: ['route-orders', route.id, route.date],
    queryFn: () => fetchRouteOrders(route.id, route.date),
  });

  const assignMutation = useMutation({
    mutationFn: (orderIds: string[]) => assignOrdersToRoute(route.id, orderIds),
    onMutate: async (orderIds: string[]) => {
      await qc.cancelQueries({ queryKey: ['unassigned', route.date] });
      await qc.cancelQueries({ queryKey: ['route-orders', route.id, route.date] });
      const prevUnassigned =
        qc.getQueryData<Order[]>(['unassigned', route.date]) || [];
      const prevAssigned =
        qc.getQueryData<Order[]>(['route-orders', route.id, route.date]) || [];
      const moved = prevUnassigned.filter((o) => orderIds.includes(o.id));
      qc.setQueryData<Order[]>(
        ['unassigned', route.date],
        prevUnassigned.filter((o) => !orderIds.includes(o.id)),
      );
      if (moved.length > 0) {
        qc.setQueryData<Order[]>(
          ['route-orders', route.id, route.date],
          [...prevAssigned, ...moved],
        );
      }
      return { prevUnassigned, prevAssigned };
    },
    onError: (_err, _orderIds, ctx) => {
      if (ctx) {
        qc.setQueryData(['unassigned', route.date], ctx.prevUnassigned);
        qc.setQueryData(
          ['route-orders', route.id, route.date],
          ctx.prevAssigned,
        );
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['routes', route.date] });
      qc.invalidateQueries({ queryKey: ['unassigned', route.date] });
      qc.invalidateQueries({ queryKey: ['route-orders', route.id, route.date] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (orderId: string) => removeOrdersFromRoute(route.id, [orderId]),
    onMutate: async (orderId: string) => {
      await qc.cancelQueries({ queryKey: ['unassigned', route.date] });
      await qc.cancelQueries({ queryKey: ['route-orders', route.id, route.date] });
      const prevUnassigned =
        qc.getQueryData<Order[]>(['unassigned', route.date]) || [];
      const prevAssigned =
        qc.getQueryData<Order[]>(['route-orders', route.id, route.date]) || [];
      const order = prevAssigned.find((o) => o.id === orderId);
      qc.setQueryData<Order[]>(
        ['route-orders', route.id, route.date],
        prevAssigned.filter((o) => o.id !== orderId),
      );
      if (order) {
        qc.setQueryData<Order[]>(
          ['unassigned', route.date],
          [...prevUnassigned, order],
        );
      }
      return { prevUnassigned, prevAssigned };
    },
    onError: (_err, _orderId, ctx) => {
      if (ctx) {
        qc.setQueryData(['unassigned', route.date], ctx.prevUnassigned);
        qc.setQueryData([
          'route-orders',
          route.id,
          route.date,
        ], ctx.prevAssigned);
      }
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ['routes', route.date] });
      qc.invalidateQueries({ queryKey: ['unassigned', route.date] });
      qc.invalidateQueries({ queryKey: ['route-orders', route.id, route.date] });
    },
  });

  const dialogRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    const el = dialogRef.current;
    const prev = document.activeElement as HTMLElement | null;
    el?.focus();
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
      if (e.key === 'Tab' && el) {
        const focusable = Array.from(
          el.querySelectorAll<HTMLElement>(
            'a,button,input,select,textarea,[tabindex]:not([tabindex="-1"])'
          )
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    el?.addEventListener('keydown', handleKeyDown);
    return () => {
      el?.removeEventListener('keydown', handleKeyDown);
      prev?.focus();
    };
  }, [onClose]);

  const [selected, setSelected] = React.useState<string[]>([]);
  const [viewMode, setViewMode] = React.useState<'list' | 'clusters'>('list');
  
  const toggle = (id: string, checked: boolean) => {
    setSelected((prev) => {
      if (checked) return [...prev, id];
      return prev.filter((x) => x !== id);
    });
  };

  const groupOrdersByArea = (orders: Order[]) => {
    const groups: Record<string, Order[]> = {};
    orders.forEach(order => {
      const address = order.customerAddress || order.address || 'No address';
      const area = extractArea(address);
      if (!groups[area]) groups[area] = [];
      groups[area].push(order);
    });
    return Object.entries(groups).sort(([, a], [, b]) => b.length - a.length);
  };

  const extractArea = (address: string) => {
    if (address === 'No address') return 'No address';
    const parts = address.split(',').map(p => p.trim());
    if (parts.length >= 2) {
      return parts[parts.length - 2] || parts[parts.length - 1];
    }
    return parts[0] || 'Unknown area';
  };

  const handleAddSelected = () => {
    if (selected.length === 0) return;
    assignMutation.mutate(selected);
    setSelected([]);
  };

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="route-title"
      tabIndex={-1}
      style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 360, background: '#fff', boxShadow: '-2px 0 8px rgba(0,0,0,0.2)', padding: 16, overflowY: 'auto' }}
    >
      <button onClick={onClose} aria-label="Close" style={{ float: 'right' }}>✕</button>
      <h2 id="route-title">{route.name}</h2>
      <h3>Stops</h3>
      <table className="table">
        <thead>
          <tr><th>Seq</th><th>Order</th><th>Address</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          {assignedQuery.isLoading && (
            <tr>
              <td colSpan={5} role="status">Loading...</td>
            </tr>
          )}
          {assignedQuery.isError && (
            <tr>
              <td colSpan={5} role="alert">Failed to load</td>
            </tr>
          )}
          {!assignedQuery.isLoading &&
            (assignedQuery.data || []).map((o: Order, idx: number) => (
              <tr key={o.id}>
                <td>{idx + 1}</td>
                <td>
                  <div style={{ fontSize: '0.9em', fontWeight: 500 }}>{o.orderNo}</div>
                  {o.customerName && (
                    <div style={{ fontSize: '0.8em', color: 'var(--color-border-muted)' }}>
                      {o.customerName}
                    </div>
                  )}
                </td>
                <td style={{ fontSize: '0.8em', maxWidth: '120px', wordWrap: 'break-word' }}>
                  {o.customerAddress || o.address || 'No address'}
                </td>
                <td>{o.status}</td>
                <td>
                  <button onClick={() => removeMutation.mutate(o.id)}>Remove</button>
                </td>
              </tr>
            ))}
          {!assignedQuery.isLoading && (assignedQuery.data?.length || 0) === 0 && (
            <tr><td colSpan={5} style={{ opacity: 0.6 }}>No stops</td></tr>
          )}
        </tbody>
      </table>
      {unassigned && unassigned.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
            <h3 style={{ margin: 0 }}>Add from Unassigned</h3>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setViewMode(viewMode === 'list' ? 'clusters' : 'list')}
                style={{ fontSize: '0.8em', padding: '4px 8px', background: 'var(--color-border)', border: 'none', borderRadius: '4px', cursor: 'pointer' }}
              >
                {viewMode === 'list' ? '📍 Cluster' : '📋 List'}
              </button>
            </div>
          </div>
          <button
            onClick={handleAddSelected}
            disabled={selected.length === 0}
            style={{ marginBottom: 12 }}
          >
            Add Selected ({selected.length})
          </button>
          {viewMode === 'list' ? (
            <ul style={{ listStyle: 'none', padding: 0 }}>
              {unassigned.map((o: Order) => (
                <li key={o.id} style={{ marginBottom: 8, padding: 8, border: '1px solid var(--color-border)', borderRadius: '4px' }}>
                  <label style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={selected.includes(o.id)}
                      onChange={(e) => toggle(o.id, e.target.checked)}
                      style={{ marginTop: 2 }}
                    />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '0.9em', fontWeight: 500, marginBottom: 2 }}>
                        {o.orderNo}
                        {o.customerName && (
                          <span style={{ marginLeft: 8, fontSize: '0.8em', fontWeight: 'normal', color: 'var(--color-border-muted)' }}>
                            {o.customerName}
                          </span>
                        )}
                      </div>
                      <div style={{ fontSize: '0.8em', color: 'var(--color-text)', marginBottom: 4, wordWrap: 'break-word' }}>
                        📍 {o.customerAddress || o.address || 'No address'}
                      </div>
                      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                        {getOrderBadges(o, route.date).map((b) => (
                          <span key={b} style={{ fontSize: '0.7em', background: '#fee', color: '#c00', padding: '2px 6px', borderRadius: '12px' }}>
                            {b}
                          </span>
                        ))}
                      </div>
                    </div>
                  </label>
                </li>
              ))}
            </ul>
          ) : (
            <div>
              {groupOrdersByArea(unassigned).map(([area, orders]) => (
                <div key={area} style={{ marginBottom: 16, border: '1px solid var(--color-border)', borderRadius: '6px', overflow: 'hidden' }}>
                  <div style={{ 
                    background: 'var(--color-bg-secondary)', 
                    padding: '8px 12px', 
                    fontSize: '0.9em', 
                    fontWeight: 500,
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center'
                  }}>
                    <span>📍 {area}</span>
                    <span style={{ fontSize: '0.8em', color: 'var(--color-border-muted)' }}>
                      {orders.length} order{orders.length !== 1 ? 's' : ''}
                    </span>
                  </div>
                  <div style={{ padding: '4px' }}>
                    {orders.map((o: Order) => (
                      <label key={o.id} style={{ 
                        display: 'flex', 
                        alignItems: 'flex-start', 
                        gap: 8, 
                        cursor: 'pointer',
                        padding: '6px 8px',
                        borderRadius: '4px',
                        margin: '2px 0'
                      }}>
                        <input
                          type="checkbox"
                          checked={selected.includes(o.id)}
                          onChange={(e) => toggle(o.id, e.target.checked)}
                          style={{ marginTop: 2 }}
                        />
                        <div style={{ flex: 1, minWidth: 0 }}>
                          <div style={{ fontSize: '0.85em', marginBottom: 2 }}>
                            <span style={{ fontWeight: 500 }}>{o.orderNo}</span>
                            {o.customerName && (
                              <span style={{ marginLeft: 8, color: 'var(--color-border-muted)' }}>
                                {o.customerName}
                              </span>
                            )}
                          </div>
                          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 3 }}>
                            {getOrderBadges(o, route.date).map((b) => (
                              <span key={b} style={{ fontSize: '0.65em', background: '#fee', color: '#c00', padding: '1px 4px', borderRadius: '8px' }}>
                                {b}
                              </span>
                            ))}
                          </div>
                        </div>
                      </label>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

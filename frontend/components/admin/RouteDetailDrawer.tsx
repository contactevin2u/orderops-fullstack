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
  const toggle = (id: string, checked: boolean) => {
    setSelected((prev) => {
      if (checked) return [...prev, id];
      return prev.filter((x) => x !== id);
    });
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
          <tr><th>Seq</th><th>Order</th><th>Status</th><th></th></tr>
        </thead>
        <tbody>
          {assignedQuery.isLoading && (
            <tr>
              <td colSpan={4} role="status">Loading...</td>
            </tr>
          )}
          {assignedQuery.isError && (
            <tr>
              <td colSpan={4} role="alert">Failed to load</td>
            </tr>
          )}
          {!assignedQuery.isLoading &&
            (assignedQuery.data || []).map((o: Order, idx: number) => (
              <tr key={o.id}>
                <td>{idx + 1}</td>
                <td>{o.orderNo}</td>
                <td>{o.status}</td>
                <td>
                  <button onClick={() => removeMutation.mutate(o.id)}>Remove</button>
                </td>
              </tr>
            ))}
          {!assignedQuery.isLoading && (assignedQuery.data?.length || 0) === 0 && (
            <tr><td colSpan={4} style={{ opacity: 0.6 }}>No stops</td></tr>
          )}
        </tbody>
      </table>
      {unassigned && unassigned.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Add from Unassigned</h3>
          <button
            onClick={handleAddSelected}
            disabled={selected.length === 0}
            style={{ marginBottom: 8 }}
          >
            Add Selected
          </button>
          <ul>
            {unassigned.map((o: Order) => (
              <li key={o.id} style={{ marginBottom: 4 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                  <input
                    type="checkbox"
                    checked={selected.includes(o.id)}
                    onChange={(e) => toggle(o.id, e.target.checked)}
                  />
                  <span>{o.orderNo}</span>
                  {getOrderBadges(o, route.date).map((b) => (
                    <span key={b} style={{ marginLeft: 4, fontSize: '0.8em', color: '#c00' }}>
                      {b}
                    </span>
                  ))}
                </label>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

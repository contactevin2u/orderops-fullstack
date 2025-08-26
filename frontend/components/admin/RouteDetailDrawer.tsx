import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Route, Order } from '@/utils/apiAdapter';
import {
  fetchUnassigned,
  assignOrdersToRoute,
  removeOrdersFromRoute,
  fetchRouteOrders,
} from '@/utils/apiAdapter';

interface Props {
  route: Route;
  onClose: () => void;
}

export default function RouteDetailDrawer({ route, onClose }: Props) {
  const qc = useQueryClient();
  const { data: unassigned } = useQuery({
    queryKey: ['unassigned', route.date],
    queryFn: () => fetchUnassigned(route.date),
  });

  const assignedQuery = useQuery({
    queryKey: ['route-orders', route.id, route.date],
    queryFn: () => fetchRouteOrders(route.id, route.date),
  });

  const assignMutation = useMutation({
    mutationFn: (orderId: string) => assignOrdersToRoute(route.id, [orderId]),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routes', route.date] });
      qc.invalidateQueries({ queryKey: ['unassigned', route.date] });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (orderId: string) => removeOrdersFromRoute(route.id, [orderId]),
    onSuccess: () =>
      qc.invalidateQueries({ queryKey: ['routes', route.date] }),
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
          <tr><th>Seq</th><th>Order</th><th></th></tr>
        </thead>
        <tbody>
          {assignedQuery.isLoading && (
            <tr>
              <td colSpan={3} role="status">Loading...</td>
            </tr>
          )}
          {assignedQuery.isError && (
            <tr>
              <td colSpan={3} role="alert">Failed to load</td>
            </tr>
          )}
          {!assignedQuery.isLoading &&
            (assignedQuery.data || []).map((o: Order, idx: number) => (
              <tr key={o.id}>
                <td>{idx + 1}</td>
                <td>{o.orderNo}</td>
                <td>
                  <button onClick={() => removeMutation.mutate(o.id)}>Remove</button>
                </td>
              </tr>
            ))}
          {!assignedQuery.isLoading && (assignedQuery.data?.length || 0) === 0 && (
            <tr><td colSpan={3} style={{ opacity: 0.6 }}>No stops</td></tr>
          )}
        </tbody>
      </table>
      {unassigned && unassigned.length > 0 && (
        <div style={{ marginTop: 24 }}>
          <h3>Add from Unassigned</h3>
          <ul>
            {unassigned.map((o: Order) => (
              <li key={o.id} style={{ marginBottom: 4 }}>
                {o.orderNo}{' '}
                <button onClick={() => assignMutation.mutate(o.id)}>Add</button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

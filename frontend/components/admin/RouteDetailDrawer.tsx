import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import type { Route, Order } from '@/utils/apiAdapter';
import { fetchUnassigned, assignOrdersToRoute, removeOrdersFromRoute } from '@/utils/apiAdapter';

interface Props {
  route: Route;
  onClose: () => void;
}

export default function RouteDetailDrawer({ route, onClose }: Props) {
  const qc = useQueryClient();
  const { data: unassigned } = useQuery(['unassigned', route.date], () => fetchUnassigned(route.date));

  const assignMutation = useMutation((orderId: string) => assignOrdersToRoute(route.id, [orderId]), {
    onSuccess: () => {
      qc.invalidateQueries(['routes', route.date]);
      qc.invalidateQueries(['unassigned', route.date]);
    },
  });

  const removeMutation = useMutation((orderId: string) => removeOrdersFromRoute(route.id, [orderId]), {
    onSuccess: () => qc.invalidateQueries(['routes', route.date]),
  });

  return (
    <div style={{ position: 'fixed', top: 0, right: 0, bottom: 0, width: 360, background: '#fff', boxShadow: '-2px 0 8px rgba(0,0,0,0.2)', padding: 16, overflowY: 'auto' }}>
      <button onClick={onClose} style={{ float: 'right' }}>✕</button>
      <h2>{route.name}</h2>
      <h3>Stops</h3>
      <table className="table">
        <thead>
          <tr><th>Seq</th><th>Order</th><th></th></tr>
        </thead>
        <tbody>
          {route.stops.map((s) => (
            <tr key={s.orderId}>
              <td>{s.seq}</td>
              <td>{s.orderId}</td>
              <td>
                <button onClick={() => removeMutation.mutate(s.orderId)}>Remove</button>
              </td>
            </tr>
          ))}
          {route.stops.length === 0 && <tr><td colSpan={3} style={{ opacity: 0.6 }}>No stops</td></tr>}
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

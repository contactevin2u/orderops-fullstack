import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRoutes, assignOrdersToRoute } from '@/utils/apiAdapter';

interface Props {
  orderIds: string[];
  date: string;
  onClose: () => void;
}

export default function AssignToRouteModal({ orderIds, date, onClose }: Props) {
  const { data: routes } = useQuery({
    queryKey: ['routes', date],
    queryFn: () => fetchRoutes(date),
  });
  const qc = useQueryClient();
  const [routeId, setRouteId] = useState('');

  const mutation = useMutation({
    mutationFn: () => assignOrdersToRoute(routeId, orderIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routes', date] });
      qc.invalidateQueries({ queryKey: ['unassigned', date] });
      onClose();
    },
  });

  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.3)' }}>
      <div style={{ background: '#fff', padding: 16, maxWidth: 320, margin: '10% auto' }}>
        <h3>Assign to route</h3>
        <select value={routeId} onChange={(e) => setRouteId(e.target.value)}>
          <option value="">Select route</option>
          {routes?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>
        <div style={{ marginTop: 16 }}>
          <button onClick={() => mutation.mutate()} disabled={!routeId}>
            Assign
          </button>{' '}
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

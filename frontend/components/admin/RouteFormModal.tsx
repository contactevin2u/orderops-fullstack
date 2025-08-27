import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDrivers, createRoute, updateRoute } from '@/utils/apiAdapter';

interface Props {
  date: string;
  route?: { id: string; driverId?: string | null; name: string };
  onClose: () => void;
}

export default function RouteFormModal({ date, route, onClose }: Props) {
  const { data: drivers, isLoading, isError } = useQuery({
    queryKey: ['drivers'],
    queryFn: fetchDrivers,
  });
  const [driverId, setDriverId] = React.useState(route?.driverId || '');
  const [name, setName] = React.useState(route?.name || '');
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () =>
      route
        ? updateRoute(route.id, {
            driver_id: Number(driverId),
            name: name || undefined,
          })
        : createRoute({
            driver_id: Number(driverId),
            route_date: date,
            name: name || undefined,
          }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routes', date] });
      onClose();
    },
  });
  return (
    <div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        background: 'rgba(0,0,0,0.3)',
      }}
    >
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="route-form-title"
        tabIndex={-1}
        style={{ background: '#fff', padding: 16, maxWidth: 320, margin: '10% auto' }}
      >
        <h3 id="route-form-title">{route ? 'Edit route' : 'Create route'}</h3>
        {isLoading && <div role="status">Loading...</div>}
        {isError && <div role="alert">Failed to load</div>}
        {!isLoading && !isError && (
          <>
            <label>
              <span>Driver</span>
              <select value={driverId} onChange={(e) => setDriverId(e.target.value)}>
                <option value="">Select driver</option>
                {drivers?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name || d.id}
                  </option>
                ))}
              </select>
            </label>
            <label style={{ display: 'block', marginTop: 8 }}>
              <span>Name</span>
              <input value={name} onChange={(e) => setName(e.target.value)} />
            </label>
          </>
        )}
        <div style={{ marginTop: 16 }}>
          <button onClick={() => mutation.mutate()} disabled={!driverId || mutation.isPending}>
            {route ? 'Save' : 'Create'}
          </button>{' '}
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}


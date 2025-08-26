import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { fetchRoutes, fetchUnassigned, fetchOnHold, Route } from '@/utils/apiAdapter';

const RouteDetailDrawer = dynamic(() => import('@/components/admin/RouteDetailDrawer'));

export default function AdminRoutesPage() {
  const router = useRouter();
  const dateParam = typeof router.query.date === 'string' ? router.query.date : '';
  const today = new Date().toISOString().slice(0, 10);
  const date = dateParam || today;

  React.useEffect(() => {
    if (!dateParam) {
      router.replace({ pathname: router.pathname, query: { date } });
    }
  }, [dateParam, date, router]);

  const { data: routes } = useQuery({
    queryKey: ['routes', date],
    queryFn: () => fetchRoutes(date),
  });
  const { data: unassigned } = useQuery({
    queryKey: ['unassigned', date],
    queryFn: () => fetchUnassigned(date),
  });
  const { data: onHold } = useQuery({
    queryKey: ['onHold', date],
    queryFn: () => fetchOnHold(date),
  });

  const [selectedRoute, setSelectedRoute] = React.useState<Route | null>(null);

  return (
    <div style={{ padding: 16 }}>
      <header style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <input
          type="date"
          value={date}
          onChange={(e) => router.push({ pathname: '/admin/routes', query: { date: e.target.value } })}
        />
        <span>Routes: {routes?.length || 0}</span>
        <span>Unassigned: {unassigned?.length || 0}</span>
        <span>On Hold: {onHold?.length || 0}</span>
      </header>
      <div style={{ marginTop: 16, display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 8 }}>
        {routes?.map((r) => (
          <div
            key={r.id}
            style={{ border: '1px solid #ccc', padding: 8, cursor: 'pointer' }}
            onClick={() => setSelectedRoute(r)}
          >
            <div style={{ fontWeight: 'bold' }}>{r.name}</div>
            <div>Driver: {r.driverId || '-'}</div>
            <div>Stops: {r.stops.length}</div>
          </div>
        ))}
      </div>
      {selectedRoute && (
        <RouteDetailDrawer route={selectedRoute} onClose={() => setSelectedRoute(null)} />
      )}
    </div>
  );
}

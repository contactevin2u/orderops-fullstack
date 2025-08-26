import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import { fetchRoutes, fetchUnassigned, fetchOnHold, Route } from '@/utils/apiAdapter';
import AdminLayout from '@/components/admin/AdminLayout';

const RouteDetailDrawer = dynamic(() => import('@/components/admin/RouteDetailDrawer'));

export function RouteCard({ route, onSelect }: { route: Route; onSelect: (r: Route) => void }) {
  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      onSelect(route);
    }
  };
  return (
    <article
      tabIndex={0}
      role="button"
      onClick={() => onSelect(route)}
      onKeyDown={onKeyDown}
      style={{ border: '1px solid #ccc', padding: 8, cursor: 'pointer' }}
    >
      <h2 style={{ marginTop: 0 }}>{route.name}</h2>
      <div>Driver: {route.driverId || '-'}</div>
      <div>Stops: {route.stops.length}</div>
    </article>
  );
}

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

  const routesQuery = useQuery({
    queryKey: ['routes', date],
    queryFn: () => fetchRoutes(date),
  });
  const unassignedQuery = useQuery({
    queryKey: ['unassigned', date],
    queryFn: () => fetchUnassigned(date),
  });
  const onHoldQuery = useQuery({
    queryKey: ['onHold', date],
    queryFn: () => fetchOnHold(date),
  });
  const routes = routesQuery.data || [];
  const unassigned = unassignedQuery.data || [];
  const onHold = onHoldQuery.data || [];

  const [selectedRoute, setSelectedRoute] = React.useState<Route | null>(null);

  return (
    <div style={{ padding: 16 }}>
      <h1>Routes</h1>
      <header style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span>Date</span>
          <input
            type="date"
            value={date}
            onChange={(e) => router.push({ pathname: '/admin/routes', query: { date: e.target.value } })}
          />
        </label>
        <span aria-live="polite">Routes: {routes.length} Unassigned: {unassigned.length} On Hold: {onHold.length}</span>
      </header>
      <div style={{ marginTop: 16 }}>
        {routesQuery.isLoading && <p role="status">Loading...</p>}
        {routesQuery.isError && (
          <p role="alert">
            {(routesQuery.error as any)?.message || 'Failed to load'}
          </p>
        )}
        {!routesQuery.isLoading && routes.length === 0 && <p style={{ opacity: 0.6 }}>No routes</p>}
        {!routesQuery.isLoading && routes.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 8 }}>
            {routes.map((r) => (
              <RouteCard key={r.id} route={r} onSelect={setSelectedRoute} />
            ))}
          </div>
        )}
      </div>
      {selectedRoute && (
        <RouteDetailDrawer route={selectedRoute} onClose={() => setSelectedRoute(null)} />
      )}
    </div>
  );
}

(AdminRoutesPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

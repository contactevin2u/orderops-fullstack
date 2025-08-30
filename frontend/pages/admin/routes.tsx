import React from 'react';
import { useRouter } from 'next/router';
import dynamic from 'next/dynamic';
import { useQuery } from '@tanstack/react-query';
import {
  fetchRoutes,
  fetchUnassigned,
  fetchOnHold,
  fetchDrivers,
  Route,
} from '@/utils/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';
import AdminLayout from '@/components/admin/AdminLayout';

const RouteDetailDrawer = dynamic(() => import('@/components/admin/RouteDetailDrawer'));
const RouteFormModal = dynamic(() => import('@/components/admin/RouteFormModal'));

export function RouteCard({
  route,
  onSelect,
  onEdit,
  driverName,
}: {
  route: Route;
  onSelect: (r: Route) => void;
  onEdit: (r: Route) => void;
  driverName?: string;
}) {
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
      <div>Driver: {driverName || '-'}</div>
      <div>Stops: —</div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onEdit(route);
        }}
      >
        Edit
      </button>
    </article>
  );
}

export default function AdminRoutesPage() {
  const router = useRouter();
  const dateParam = typeof router.query.date === 'string' ? router.query.date : '';
  const today = new Date().toLocaleDateString('en-CA');
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
  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: fetchDrivers,
  });
  const routes = React.useMemo(() => routesQuery.data || [], [routesQuery.data]);
  const unassigned = React.useMemo(() => unassignedQuery.data || [], [unassignedQuery.data]);
  const onHold = React.useMemo(() => onHoldQuery.data || [], [onHoldQuery.data]);
  const drivers = React.useMemo(() => driversQuery.data || [], [driversQuery.data]);

  const driverNameById = React.useMemo(() => {
    const map: Record<string, string> = {};
    drivers.forEach((d) => {
      map[d.id] = d.name || '';
    });
    return map;
  }, [drivers]);

  const counts = React.useMemo(() => {
    let noDate = 0;
    let overdue = 0;
    unassigned.forEach((o) => {
      const badges = getOrderBadges(o, date);
      if (badges.includes('No date')) noDate += 1;
      if (badges.some((b) => b.startsWith('Overdue'))) overdue += 1;
    });
    return { noDate, overdue };
  }, [unassigned, date]);

  const [selectedRoute, setSelectedRoute] = React.useState<Route | null>(null);
  const [creating, setCreating] = React.useState(false);
  const [editingRoute, setEditingRoute] = React.useState<Route | null>(null);

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
        <button onClick={() => setCreating(true)}>Create Route</button>
        <span aria-live="polite">
          Routes: {routes.length} Unassigned: {unassigned.length} (No date: {counts.noDate} Overdue: {counts.overdue}) On Hold: {onHold.length}
        </span>
      </header>
      <div style={{ marginTop: 16 }}>
        {routesQuery.isLoading && <p role="status">Loading...</p>}
        {routesQuery.isError && <p role="alert">Failed to load</p>}
        {!routesQuery.isLoading && routes.length === 0 && <p style={{ opacity: 0.6 }}>No routes</p>}
        {!routesQuery.isLoading && routes.length > 0 && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(220px,1fr))', gap: 8 }}>
            {routes.map((r) => (
              <RouteCard
                key={r.id}
                route={r}
                onSelect={setSelectedRoute}
                onEdit={setEditingRoute}
                driverName={driverNameById[r.driverId || '']}
              />
            ))}
          </div>
        )}
      </div>
      {selectedRoute && (
        <RouteDetailDrawer route={selectedRoute} onClose={() => setSelectedRoute(null)} />
      )}
      {creating && <RouteFormModal date={date} onClose={() => setCreating(false)} />}
      {editingRoute && (
        <RouteFormModal
          date={date}
          route={editingRoute}
          onClose={() => setEditingRoute(null)}
        />
      )}
    </div>
  );
}

(AdminRoutesPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

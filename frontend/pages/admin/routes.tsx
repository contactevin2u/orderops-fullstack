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
} from '@/lib/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';
import AdminLayout from '@/components/Layout/AdminLayout';

const RouteDetailDrawer = dynamic(() => import('@/components/admin/RouteDetailDrawer'));
const RouteFormModal = dynamic(() => import('@/components/admin/RouteFormModal'));

export function RouteCard({
  route,
  onSelect,
  onEdit,
  driverName,
  secondaryDriverName,
}: {
  route: Route;
  onSelect: (r: Route) => void;
  onEdit: (r: Route) => void;
  driverName?: string;
  secondaryDriverName?: string;
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
      className="card cursor-pointer"
      style={{
        transition: 'box-shadow 0.2s',
        outline: 'none'
      }}
      onMouseEnter={(e) => {
        (e.target as HTMLElement).style.boxShadow = 'var(--shadow-lg)';
      }}
      onMouseLeave={(e) => {
        (e.target as HTMLElement).style.boxShadow = '';
      }}
      onFocus={(e) => {
        (e.target as HTMLElement).style.outline = '2px solid var(--color-primary)';
        (e.target as HTMLElement).style.outlineOffset = '2px';
      }}
      onBlur={(e) => {
        (e.target as HTMLElement).style.outline = 'none';
      }}
    >
      <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-2)' }}>{route.name}</h2>
      <div style={{ marginBottom: 'var(--space-4)' }}>
        <div className="cluster" style={{ fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
          <span style={{ fontWeight: 500 }}>Primary:</span>
          <span style={{ color: driverName ? 'var(--color-text)' : 'var(--color-border-muted)' }}>
            {driverName || 'Unassigned'}
          </span>
        </div>
        {secondaryDriverName && (
          <div className="cluster" style={{ fontSize: '0.875rem', marginBottom: 'var(--space-1)' }}>
            <span style={{ fontWeight: 500 }}>Secondary:</span>
            <span>{secondaryDriverName}</span>
          </div>
        )}
        <div className="cluster" style={{ fontSize: '0.875rem' }}>
          <span style={{ fontWeight: 500 }}>Stops:</span>
          <span style={{ color: 'var(--color-border-muted)' }}>{route.stops.length}</span>
        </div>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onEdit(route);
        }}
        className="btn secondary"
        style={{ fontSize: '0.875rem', minHeight: 'auto', padding: 'var(--space-2) var(--space-3)' }}
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
    <div className="main">
      <div className="container">
        <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-6)' }}>Routes</h1>
        <header className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <div className="cluster">
            <label className="cluster" style={{ fontSize: '0.875rem' }}>
              <span style={{ fontWeight: 500 }}>Date:</span>
              <input
                type="date"
                value={date}
                onChange={(e) => router.push({ pathname: '/admin/routes', query: { date: e.target.value } })}
                className="input"
                style={{ fontSize: '0.875rem' }}
              />
            </label>
            <button onClick={() => setCreating(true)} className="btn">
              Create Route
            </button>
            <div style={{ fontSize: '0.875rem' }} aria-live="polite">
              <div className="cluster">
                <span className="cluster">
                  <span style={{ fontWeight: 500, color: '#2563eb' }}>{routes.length}</span>
                  <span>Routes</span>
                </span>
                <span className="cluster">
                  <span style={{ fontWeight: 500, color: '#ea580c' }}>{unassigned.length}</span>
                  <span>Unassigned</span>
                </span>
                <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                  (No date: {counts.noDate}, Overdue: {counts.overdue})
                </span>
                <span className="cluster">
                  <span style={{ fontWeight: 500, color: '#9333ea' }}>{onHold.length}</span>
                  <span>On Hold</span>
                </span>
              </div>
            </div>
          </div>
        </header>
        <div>
          {routesQuery.isLoading && (
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-10) 0' }} role="status">
              <div style={{
                width: '2rem',
                height: '2rem',
                border: '2px solid var(--color-border)',
                borderTop: '2px solid var(--color-primary)',
                borderRadius: '50%',
                animation: 'spin 1s linear infinite'
              }}></div>
              <span style={{ marginLeft: 'var(--space-3)' }}>Loading routes...</span>
            </div>
          )}
          {routesQuery.isError && (
            <div
              style={{
                background: '#fef2f2',
                border: '1px solid #fecaca',
                color: '#b91c1c',
                padding: 'var(--space-3) var(--space-4)',
                borderRadius: 'var(--radius-2)'
              }}
              role="alert"
            >
              Failed to load routes. Please try again.
            </div>
          )}
          {!routesQuery.isLoading && routes.length === 0 && (
            <div style={{ textAlign: 'center', padding: 'var(--space-10) 0' }}>
              <div style={{ color: 'var(--color-border-muted)', fontSize: '1.125rem', marginBottom: 'var(--space-2)' }}>
                No routes found
              </div>
              <p style={{ opacity: 0.7, fontSize: '0.875rem' }}>Create your first route to get started</p>
            </div>
          )}
          {!routesQuery.isLoading && routes.length > 0 && (
            <div className="grid" style={{
              gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
              gap: 'var(--space-6)'
            }}>
              {routes.map((r) => (
                <RouteCard
                  key={r.id}
                  route={r}
                  onSelect={setSelectedRoute}
                  onEdit={setEditingRoute}
                  driverName={driverNameById[r.driverId || '']}
                  secondaryDriverName={driverNameById[r.secondaryDriverId || '']}
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
      <style jsx>{`
        @keyframes spin {
          from {
            transform: rotate(0deg);
          }
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </div>
  );
}

(AdminRoutesPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

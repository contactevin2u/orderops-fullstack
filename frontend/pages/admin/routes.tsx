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
      className="card cursor-pointer hover:shadow-lg transition-shadow duration-200 focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2"
    >
      <h2 className="text-lg font-semibold text-gray-900 mb-2">{route.name}</h2>
      <div className="space-y-1 text-sm text-gray-600 mb-4">
        <div className="flex items-center gap-2">
          <span className="font-medium">Primary:</span>
          <span className={driverName ? 'text-gray-900' : 'text-gray-400'}>
            {driverName || 'Unassigned'}
          </span>
        </div>
        {secondaryDriverName && (
          <div className="flex items-center gap-2">
            <span className="font-medium">Secondary:</span>
            <span className="text-gray-900">{secondaryDriverName}</span>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className="font-medium">Stops:</span>
          <span className="text-gray-400">—</span>
        </div>
      </div>
      <button
        onClick={(e) => {
          e.stopPropagation();
          onEdit(route);
        }}
        className="btn btn-secondary text-sm px-3 py-1.5 min-h-0"
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
    <div className="container">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Routes</h1>
      <header className="cluster mb-6 p-4 bg-white rounded-lg border border-gray-200">
        <label className="cluster text-sm">
          <span className="font-medium text-gray-700">Date:</span>
          <input
            type="date"
            value={date}
            onChange={(e) => router.push({ pathname: '/admin/routes', query: { date: e.target.value } })}
            className="input text-sm"
          />
        </label>
        <button onClick={() => setCreating(true)} className="btn btn-primary">
          Create Route
        </button>
        <div className="text-sm text-gray-600 flex flex-wrap gap-4" aria-live="polite">
          <span className="flex items-center gap-1">
            <span className="font-medium text-blue-600">{routes.length}</span> Routes
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-orange-600">{unassigned.length}</span> Unassigned
          </span>
          <span className="text-xs text-gray-500">
            (No date: {counts.noDate}, Overdue: {counts.overdue})
          </span>
          <span className="flex items-center gap-1">
            <span className="font-medium text-purple-600">{onHold.length}</span> On Hold
          </span>
        </div>
      </header>
      <div>
        {routesQuery.isLoading && (
          <div className="flex items-center justify-center py-12" role="status">
            <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
            <span className="ml-3 text-gray-600">Loading routes...</span>
          </div>
        )}
        {routesQuery.isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg" role="alert">
            Failed to load routes. Please try again.
          </div>
        )}
        {!routesQuery.isLoading && routes.length === 0 && (
          <div className="text-center py-12">
            <div className="text-gray-400 text-lg mb-2">No routes found</div>
            <p className="text-gray-500 text-sm">Create your first route to get started</p>
          </div>
        )}
        {!routesQuery.isLoading && routes.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
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
  );
}

(AdminRoutesPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

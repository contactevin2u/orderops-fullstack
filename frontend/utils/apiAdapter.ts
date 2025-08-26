import { listRoutes, listOrders, addOrdersToRoute, createRoute as apiCreateRoute } from './api';

export type Order = {
  id: string;
  orderNo: string;
  status: string;
  deliveryDate: string;
  address: string;
  lat?: number;
  lng?: number;
  timeWindowStart?: string;
  timeWindowEnd?: string;
  size?: number;
  weightKg?: number;
  priority?: number;
  routeId?: string | null;
  notes?: string;
  trip?: any;
};

export type Route = {
  id: string;
  name: string;
  date: string;
  team?: string;
  zone?: string;
  driverId?: string | null;
  vehicleId?: string | null;
  capacity?: { stops?: number; weightKg?: number };
  stops: Array<{ orderId: string; seq: number }>;
  etaRange?: { start?: string; end?: string };
};

function mapOrder(o: any): Order {
  return {
    id: String(o.id ?? ''),
    orderNo: o.code || o.orderNo || String(o.id ?? ''),
    status: o.status || 'UNASSIGNED',
    deliveryDate: o.delivery_date || o.deliveryDate || '',
    address:
      o.address ||
      [o.address1, o.address2].filter(Boolean).join(' ') ||
      o.customer_address ||
      '',
    lat: o.lat ?? o.latitude ?? o.location?.lat,
    lng: o.lng ?? o.longitude ?? o.location?.lng,
    timeWindowStart: o.time_window_start || o.timeWindowStart || o.window_start,
    timeWindowEnd: o.time_window_end || o.timeWindowEnd || o.window_end,
    size: o.size,
    weightKg: o.weight_kg ?? o.weightKg,
    priority: o.priority,
    routeId: o.route_id ?? o.routeId ?? o.trip?.route_id ?? null,
    notes: o.notes || '',
    trip: o.trip,
  };
}

function mapRoute(r: any): Route {
  return {
    id: String(r.id ?? ''),
    name: r.name || `Route ${r.id}`,
    date: r.route_date || r.date || '',
    team: r.team,
    zone: r.zone,
    driverId: r.driver_id?.toString() ?? r.driverId ?? null,
    vehicleId: r.vehicle_id?.toString() ?? r.vehicleId ?? null,
    capacity: r.capacity
      ? {
          stops: r.capacity.stops ?? r.capacity.stopsLimit,
          weightKg: r.capacity.weightKg ?? r.capacity.weight_kg,
        }
      : undefined,
    stops: Array.isArray(r.stops)
      ? r.stops.map((s: any) => ({
          orderId: String(s.order_id ?? s.orderId ?? s.id ?? ''),
          seq: s.seq ?? s.sequence ?? 0,
        }))
      : [],
    etaRange: r.eta_range || r.etaRange || undefined,
  };
}

export async function fetchRoutes(date: string): Promise<Route[]> {
  const data = await listRoutes(date);
  return Array.isArray(data) ? data.map(mapRoute) : [];
}

export async function fetchUnassigned(date: string): Promise<Order[]> {
  const { items } = await listOrders(undefined, undefined, undefined, 500, {
    date,
    unassigned: true,
  });
  return (items || []).map(mapOrder);
}

export async function fetchOnHold(date: string): Promise<Order[]> {
  const { items } = await listOrders(undefined, 'ON_HOLD', undefined, 500, { date });
  return (items || []).map(mapOrder);
}

export async function createRoute(payload: {
  driver_id: number;
  route_date: string;
  name?: string;
  notes?: string;
}): Promise<Route> {
  const r = await apiCreateRoute(payload);
  return mapRoute(r);
}

export async function assignOrdersToRoute(
  routeId: string,
  orderIds: string[],
  opts?: any
): Promise<void> {
  await addOrdersToRoute(Number(routeId), orderIds.map((o) => Number(o)));
}

function apiBase() {
  const envBase = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  return envBase || '/_api';
}

export async function removeOrdersFromRoute(
  routeId: string,
  orderIds: string[],
): Promise<void> {
  const res = await fetch(`${apiBase()}/routes/${routeId}/orders`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json', Accept: 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ order_ids: orderIds.map((o) => Number(o)) }),
  });
  if (!res.ok) {
    throw new Error(`Failed to remove orders: ${res.status}`);
  }
}

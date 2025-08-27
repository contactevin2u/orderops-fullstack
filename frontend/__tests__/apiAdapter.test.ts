import { describe, expect, it } from 'vitest';
import { fetchRoutes, fetchUnassigned, fetchOnHold, fetchRouteOrders } from '../utils/apiAdapter';

import * as api from '../utils/api';

// mock listRoutes and listOrders
vi.mock('../utils/api');

const sampleRoute = {
  id: 1,
  name: 'Route A',
  route_date: '2024-05-25',
  driver_id: 7,
  stops: [{ order_id: 10, seq: 1 }],
};

const sampleOrder = {
  id: 10,
  code: 'ORD10',
  status: 'UNASSIGNED',
  delivery_date: '2024-05-25',
  address: '123 Main',
};

describe('apiAdapter', () => {
  it('maps routes correctly', async () => {
    (api.listRoutes as any).mockResolvedValue([sampleRoute]);
    const routes = await fetchRoutes('2024-05-25');
    expect(routes[0]).toMatchObject({
      id: '1',
      name: 'Route A',
      date: '2024-05-25',
      driverId: '7',
      stops: [{ orderId: '10', seq: 1 }],
    });
  });

  it('fetchUnassigned passes server-side filters', async () => {
    (api.listOrders as any).mockResolvedValue({ items: [sampleOrder] });
    const orders = await fetchUnassigned('2024-05-25');
    expect(api.listOrders).toHaveBeenCalledWith(undefined, undefined, undefined, 500, {
      date: '2024-05-25',
      unassigned: true,
    });
    expect(orders).toHaveLength(1);
    expect(orders[0].id).toBe('10');
  });

  it('fetchOnHold forwards date and status filters', async () => {
    (api.listOrders as any).mockResolvedValue({ items: [{ ...sampleOrder, status: 'ON_HOLD' }] });
    const orders = await fetchOnHold('2024-05-25');
    expect(api.listOrders).toHaveBeenCalledWith(undefined, 'ON_HOLD', undefined, 500, {
      date: '2024-05-25',
    });
    expect(orders).toHaveLength(1);
    expect(orders[0].status).toBe('ON_HOLD');
  });

  it('fetchRouteOrders filters orders by route id', async () => {
    (api.listOrders as any).mockResolvedValue({
      items: [
        { ...sampleOrder, trip: { route_id: 1 } },
        { ...sampleOrder, id: 11, trip: { route_id: 2 } },
      ],
    });
    const orders = await fetchRouteOrders('1', '2024-05-25');
    expect(api.listOrders).toHaveBeenCalledWith(
      undefined,
      undefined,
      undefined,
      500,
    );
    expect(orders).toHaveLength(1);
    expect(orders[0].routeId).toBe('1');
  });
});

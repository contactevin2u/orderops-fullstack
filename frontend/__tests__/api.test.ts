import {
  listOrders,
  getOrder,
  listDrivers,
  assignOrderToDriver,
  listDriverCommissions,
  listDriverOrders,
} from '@/utils/api';

// Use Vitest's vi to mock fetch

vi.mock('next/headers', () => ({
  cookies: () => ({
    toString: () => 'sid=abc',
  }),
}));

describe('api request unwrapping', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it('unwraps {ok,data} envelope for listOrders', async () => {
    const items = [{ id: 1 }, { id: 2 }];
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ ok: true, data: items }),
      headers: { get: () => 'application/json' },
    });

    const result = await listOrders();
    expect(result).toEqual({ items, total: 2 });
  });

  it('unwraps {ok,data} envelope for getOrder', async () => {
    const order = { id: 123, foo: 'bar' };
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ ok: true, data: order }),
      headers: { get: () => 'application/json' },
    });

    const result = await getOrder(123);
    expect(result).toEqual(order);
  });

  it('forwards cookies on server requests', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({}),
      headers: { get: () => 'application/json' },
    });

    const savedWindow = (global as any).window;
    (global as any).window = undefined;

    await getOrder(1);

    expect((global as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/orders/1'),
      expect.objectContaining({
        headers: expect.objectContaining({ Cookie: 'sid=abc' }),
      }),
    );

    (global as any).window = savedWindow;
  });

  it('lists drivers', async () => {
    const drivers = [{ id: 'd1', name: 'Driver One' }];
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(drivers),
      headers: { get: () => 'application/json' },
    });

    const result = await listDrivers();
    expect(result).toEqual(drivers);
  });

  it('posts assignment payload', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({}),
      headers: { get: () => 'application/json' },
    });

    await assignOrderToDriver(1, 'd1');
    expect((global as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/orders/1/assign'),
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({ driver_id: 'd1' }),
      }),
    );
  });

  it('fetches driver commissions', async () => {
    const data = [{ month: '2024-01', total: 10 }];
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify(data),
      headers: { get: () => 'application/json' },
    });

    const result = await listDriverCommissions(1);
    expect(result).toEqual(data);
    expect((global as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/drivers/1/commissions'),
      expect.any(Object)
    );
  });

  it('fetches driver orders', async () => {
    const data = [{ id: 1 }];
    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      text: async () => JSON.stringify({ items: data }),
      headers: { get: () => 'application/json' },
    });

    const result = await listDriverOrders(1, '2024-01');
    expect(result).toEqual(data);
    expect((global as any).fetch).toHaveBeenCalledWith(
      expect.stringContaining('/orders?'),
      expect.any(Object)
    );
  });
});

import { ApiOrderSchema, mapOrder } from '@infra/api/schemas';
import { OrderStatus } from '@core/entities/Order';

describe('order mapping', () => {
  test('parses and maps to domain', () => {
    const api = ApiOrderSchema.parse({
      id: 1,
      status: OrderStatus.ASSIGNED,
      customer: {
        id: 2,
        name: 'John Doe',
        phone: '123',
        address: 'Street',
        mapUrl: 'url',
      },
    });
    const order = mapOrder(api);
    expect(order).toEqual({
      id: 1,
      status: OrderStatus.ASSIGNED,
      customer: {
        id: 2,
        name: 'John Doe',
        phone: '123',
        address: 'Street',
        mapUrl: 'url',
      },
    });
  });
});

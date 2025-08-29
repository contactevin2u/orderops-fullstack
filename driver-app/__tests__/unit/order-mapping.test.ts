import { ApiOrderSchema } from '@infra/api/schemas';
import { OrderStatus } from '@core/entities/Order';

jest.mock('@react-native-firebase/auth', () => ({
  __esModule: true,
  default: () => ({ currentUser: null }),
}));

jest.mock('@react-native-async-storage/async-storage', () => ({
  __esModule: true,
  default: {
    getItem: jest.fn(),
    setItem: jest.fn(),
    removeItem: jest.fn(),
  },
}));

jest.mock('@shared/constants/config', () => ({ API_BASE: '' }));

jest.mock('@infra/api/ApiClient', () => ({
  __esModule: true,
  default: {
    get: jest.fn(),
    post: jest.fn(),
    patch: jest.fn(),
    upload: jest.fn(),
  },
}));

const { mapApiOrder } = require('@infra/api/OrderRepository');

describe('order mapping', () => {
  test('parses and maps to domain', () => {
    const api = ApiOrderSchema.parse({
      id: 1,
      code: 'X',
      status: OrderStatus.ASSIGNED,
      delivery_date: '2024-01-01',
      customer: {
        id: 2,
        name: 'John Doe',
        phone: '123',
        address: 'Street',
        map_url: 'url',
      },
      pricing: { total_cents: 1000 },
    });
    const order = mapApiOrder(api);
    expect(order).toEqual({
      id: 1,
      code: 'X',
      status: OrderStatus.ASSIGNED,
      deliveryDate: '2024-01-01',
      customer: {
        id: 2,
        name: 'John Doe',
        phone: '123',
        address: 'Street',
        mapUrl: 'url',
      },
      pricing: { total_cents: 1000 },
    });
  });
});

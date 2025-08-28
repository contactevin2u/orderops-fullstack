import { on, emit, ORDER_OPEN_EVENT } from '@infra/events/bus';

describe('event bus', () => {
  test('on/emit/off', () => {
    const handler = jest.fn();
    const off = on(ORDER_OPEN_EVENT, handler);
    emit(ORDER_OPEN_EVENT, { orderId: '1' });
    expect(handler).toHaveBeenCalledWith({ orderId: '1' });
    off();
    emit(ORDER_OPEN_EVENT, { orderId: '1' });
    expect(handler).toHaveBeenCalledTimes(1);
  });
});

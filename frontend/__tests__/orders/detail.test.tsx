import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import { vi } from 'vitest';
import OrderDetailPage from '@/pages/orders/[id]';

vi.mock('next/router', () => ({ useRouter: () => ({ query: { id: '1' } }) }));
vi.mock('@/components/Layout', () => ({ default: ({ children }: any) => <div>{children}</div> }));

const mockGetOrder = vi.fn();
const mockUpdateOrder = vi.fn();
const mockOrderDue = vi.fn();

vi.mock('@/utils/api', () => ({
  getOrder: (...args: any[]) => mockGetOrder(...args),
  updateOrder: (...args: any[]) => mockUpdateOrder(...args),
  addPayment: vi.fn(),
  voidPayment: vi.fn(),
  voidOrder: vi.fn(),
  markReturned: vi.fn(),
  markBuyback: vi.fn(),
  invoicePdfUrl: vi.fn(),
  orderDue: (...args: any[]) => mockOrderDue(...args),
}));

describe('OrderDetailPage', () => {
  beforeEach(() => {
    mockGetOrder.mockReset();
    mockUpdateOrder.mockReset();
    mockOrderDue.mockReset();
  });

  it('allows editing fees and plan months', async () => {
    mockGetOrder.mockResolvedValue({
      id: 1,
      code: 'ORD1',
      status: 'NEW',
      type: 'INSTALLMENT',
      customer: {},
      items: [],
      delivery_fee: 10,
      return_delivery_fee: 5,
      plan: { plan_type: 'INSTALLMENT', months: 6, monthly_amount: 100 },
    });
    mockOrderDue.mockResolvedValue({});
    mockUpdateOrder.mockResolvedValue({});

    render(<OrderDetailPage />);

    const monthsInput = await screen.findByDisplayValue('6');
    const deliveryInput = screen.getByDisplayValue('10');

    fireEvent.change(monthsInput, { target: { value: '8' } });
    fireEvent.change(deliveryInput, { target: { value: '12' } });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => expect(mockUpdateOrder).toHaveBeenCalled());
    expect(mockUpdateOrder).toHaveBeenCalledWith(1, expect.objectContaining({
      delivery_fee: 12,
      plan: expect.objectContaining({ months: 8 }),
    }));
  });

  it('allows editing items', async () => {
    mockGetOrder.mockResolvedValue({
      id: 1,
      code: 'ORD1',
      status: 'NEW',
      type: 'OUTRIGHT',
      customer: {},
      items: [{ id: 5, name: 'Item1', item_type: 'OUTRIGHT', qty: 1, unit_price: 10, monthly_amount: 50 }],
    });
    mockOrderDue.mockResolvedValue({});
    mockUpdateOrder.mockResolvedValue({ items: [] });

    render(<OrderDetailPage />);

    const qtyInput = await screen.findByDisplayValue('1');
    const monthlyInput = screen.getByDisplayValue('50');
    fireEvent.change(qtyInput, { target: { value: '2' } });
    fireEvent.change(monthlyInput, { target: { value: '60' } });

    fireEvent.click(screen.getByText('Save Items'));

    await waitFor(() => expect(mockUpdateOrder).toHaveBeenCalled());
    expect(mockUpdateOrder).toHaveBeenCalledWith(1, {
      items: [expect.objectContaining({ id: 5, qty: 2, unit_price: 10, line_total: 20, monthly_amount: 60 })],
    });
  });

  it('allows editing customer info', async () => {
    mockGetOrder.mockResolvedValue({
      id: 1,
      code: 'ORD1',
      status: 'NEW',
      type: 'OUTRIGHT',
      customer: { name: 'John', phone: '123', address: 'Addr' },
      items: [],
    });
    mockOrderDue.mockResolvedValue({});
    mockUpdateOrder.mockResolvedValue({});

    render(<OrderDetailPage />);

    const nameInput = await screen.findByDisplayValue('John');
    fireEvent.change(nameInput, { target: { value: 'Jane' } });

    fireEvent.click(screen.getByText('Save'));

    await waitFor(() => expect(mockUpdateOrder).toHaveBeenCalled());
    expect(mockUpdateOrder).toHaveBeenCalledWith(1, expect.objectContaining({
      customer: expect.objectContaining({ name: 'Jane' }),
    }));
  });
});

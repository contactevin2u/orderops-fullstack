import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { OrderRow } from '@/pages/admin/driver-commissions';

describe('OrderRow', () => {
  const baseOrder: any = {
    id: 1,
    code: '1',
    status: 'DELIVERED',
    trip: { commission: { computed_amount: 0 }, pod_photo_url: 'https://example.com/pod.jpg' },
  };

  it('shows PDF placeholder', () => {
    const order = { ...baseOrder, trip: { pod_photo_url: 'https://example.com/pod.pdf', commission: { computed_amount: 0 } } };
    render(
      <table>
        <tbody>
          <OrderRow o={order} onPaySuccess={async () => {}} onSaveCommission={async () => {}} />
        </tbody>
      </table>
    );
    expect(screen.getByText('PDF')).toBeInTheDocument();
  });

  it('calls save and shows message', async () => {
    const save = vi.fn().mockResolvedValue(undefined);
    render(
      <table>
        <tbody>
          <OrderRow o={baseOrder} onPaySuccess={async () => {}} onSaveCommission={save} />
        </tbody>
      </table>
    );
    const input = screen.getByPlaceholderText('Commission');
    await userEvent.clear(input);
    await userEvent.type(input, '12');
    await userEvent.click(screen.getByRole('button', { name: /save/i }));
    expect(save).toHaveBeenCalled();
    expect(screen.getByText(/saved/i)).toBeInTheDocument();
  });
});

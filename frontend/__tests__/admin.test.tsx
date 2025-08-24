import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import AdminPanel from '@/pages/admin';

vi.mock('@/utils/api', () => ({
  listOrders: vi.fn().mockResolvedValue({ items: [] }),
  listDrivers: vi.fn().mockResolvedValue([]),
  assignOrderToDriver: vi.fn(),
}));

describe('AdminPanel', () => {
  it('renders form fields', async () => {
    render(<AdminPanel />);
    await waitFor(() => {
      expect(screen.getByText('Order')).toBeTruthy();
      expect(screen.getByText('Driver')).toBeTruthy();
    });
  });
});

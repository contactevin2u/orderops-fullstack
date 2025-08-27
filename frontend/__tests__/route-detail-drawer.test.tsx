import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import RouteDetailDrawer from '@/components/admin/RouteDetailDrawer';

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<any>('@tanstack/react-query');
  return {
    ...actual,
    useQuery: ({ queryKey }: any) => {
      if (Array.isArray(queryKey) && queryKey[0] === 'route-orders') {
        return {
          data: [
            {
              id: '1',
              orderNo: 'ORD1',
              status: 'ASSIGNED',
              deliveryDate: '2024-07-01',
            },
          ],
          isLoading: false,
          isError: false,
        };
      }
      if (Array.isArray(queryKey) && queryKey[0] === 'unassigned') {
        return {
          data: [
            { id: '2', orderNo: 'ORD2', deliveryDate: null },
          ],
          isLoading: false,
          isError: false,
        };
      }
      return { data: [], isLoading: false, isError: false };
    },
    useMutation: () => ({ mutate: vi.fn() }),
    useQueryClient: () => ({ invalidateQueries: vi.fn() }),
  };
});

describe('RouteDetailDrawer', () => {
  it('shows orders assigned to the route', () => {
    const route = { id: '1', name: 'Route A', date: '2024-07-01' } as any;
    render(<RouteDetailDrawer route={route} onClose={() => {}} />);
    expect(screen.getByText('ORD1')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('ASSIGNED')).toBeInTheDocument();
  });

  it('allows selecting unassigned orders', () => {
    const route = { id: '1', name: 'Route A', date: '2024-07-01' } as any;
    render(<RouteDetailDrawer route={route} onClose={() => {}} />);
    const addBtn = screen.getByText('Add Selected') as HTMLButtonElement;
    expect(addBtn.disabled).toBe(true);
    const checkbox = screen.getByRole('checkbox');
    fireEvent.click(checkbox);
    expect(addBtn.disabled).toBe(false);
  });
});


import { render, screen } from '@testing-library/react';
import React from 'react';
import useSWR from 'swr';
import { vi } from 'vitest';
import OrdersPage from '@/pages/orders';

vi.mock('next/link', () => ({ default: ({ children, ...props }: any) => <a {...props}>{children}</a> }));
vi.mock('@/components/Layout', () => ({ default: ({ children }: any) => <div>{children}</div> }));
vi.mock('swr');

const mockedUseSWR: any = useSWR;

describe('OrdersPage', () => {
  it('renders without crash while loading', () => {
    mockedUseSWR.mockReturnValue({ data: undefined, error: undefined, isLoading: true, mutate: vi.fn() });
    render(<OrdersPage />);
    expect(screen.getAllByText(/orders/i)[0]).toBeInTheDocument();
  });

  it('shows error fallback', () => {
    mockedUseSWR.mockReturnValue({ data: undefined, error: new Error('fail'), isLoading: false, mutate: vi.fn() });
    render(<OrdersPage />);
    expect(screen.getByText(/failed to load orders/i)).toBeInTheDocument();
  });
});

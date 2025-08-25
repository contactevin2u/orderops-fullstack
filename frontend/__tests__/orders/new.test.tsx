import { render, screen } from '@testing-library/react';
import React from 'react';
import { vi } from 'vitest';
import NewOrderPage from '@/pages/orders/new';

vi.mock('next/router', () => ({ useRouter: () => ({ push: vi.fn() }) }));

describe('NewOrderPage', () => {
  it('renders charges and plan fields', () => {
    render(<NewOrderPage />);
    expect(screen.getByText(/^delivery fee$/i)).toBeInTheDocument();
    expect(screen.getByText(/return delivery fee/i)).toBeInTheDocument();
    expect(screen.getByText(/plan type/i)).toBeInTheDocument();
    expect(screen.getByText(/monthly amount/i)).toBeInTheDocument();
  });
});

import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { RouterContext } from 'next/dist/shared/lib/router-context.shared-runtime';
import type { NextRouter } from 'next/router';
import { vi } from 'vitest';
import AdminAssignPage from '@/pages/admin/assign';

const orders = [
  { id: '1', orderNo: '100', deliveryDate: '2024-07-01', status: 'NEW' },
  { id: '2', orderNo: '101', deliveryDate: '2024-07-01', status: 'NEW' },
];

vi.mock('@tanstack/react-query', async () => {
  const actual = await vi.importActual<any>('@tanstack/react-query');
  return {
    ...actual,
    useQuery: () => ({ data: orders, isLoading: false, isError: false }),
  };
});

function createRouter(): NextRouter {
  return {
    pathname: '/admin/assign',
    route: '/admin/assign',
    query: { date: '2024-07-01' },
    asPath: '/admin/assign',
    basePath: '',
    push: vi.fn(),
    replace: vi.fn(),
    reload: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
    beforePopState: vi.fn(),
    events: { on: vi.fn(), off: vi.fn(), emit: vi.fn() },
    isFallback: false,
    isReady: true,
    isPreview: false,
    isLocaleDomain: false,
  } as unknown as NextRouter;
}

describe('Assign select all', () => {
  it('toggles all row checkboxes', async () => {
    const user = userEvent.setup();
    const router = createRouter();
    render(
      <RouterContext.Provider value={router}>
        <AdminAssignPage />
      </RouterContext.Provider>
    );
    const selectAll = screen.getByRole('checkbox', { name: /select all/i });
    const rowChecks = screen.getAllByRole('checkbox', { name: /select order/i });
    await user.click(selectAll);
    rowChecks.forEach((c) => expect(c).toBeChecked());
    await user.click(selectAll);
    rowChecks.forEach((c) => expect(c).not.toBeChecked());
  });
});

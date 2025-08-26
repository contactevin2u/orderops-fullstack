import React from 'react';
import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import { RouterContext } from 'next/dist/shared/lib/router-context.shared-runtime';
import type { NextRouter } from 'next/router';
import AdminNav from '@/components/admin/AdminNav';

function createRouter(pathname: string): NextRouter {
  return {
    pathname,
    route: pathname,
    query: {},
    asPath: pathname,
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

describe('AdminNav', () => {
  it('marks active link with aria-current', () => {
    const router = createRouter('/admin/routes');
    render(
      <RouterContext.Provider value={router}>
        <AdminNav />
      </RouterContext.Provider>
    );
    expect(screen.getByRole('link', { name: /routes/i })).toHaveAttribute(
      'aria-current',
      'page'
    );
  });
});

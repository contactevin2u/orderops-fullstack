import React from 'react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { vi } from 'vitest';
import { RouteCard } from '@/pages/admin/routes';

describe('RouteCard', () => {
  it('calls onSelect with keyboard', async () => {
    const route: any = { id: '1', name: 'Route A', driverId: '', stops: [] };
    const onSelect = vi.fn();
    const onEdit = vi.fn();
    render(<RouteCard route={route} onSelect={onSelect} onEdit={onEdit} />);
    const card = screen.getByRole('button', { name: /route a/i });
    card.focus();
    const user = userEvent.setup();
    await user.keyboard('{Enter}');
    card.focus();
    await user.keyboard(' ');
    expect(onSelect).toHaveBeenCalledTimes(2);
  });
});

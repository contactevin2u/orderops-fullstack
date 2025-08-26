import { describe, it, expect } from 'vitest';
import { getOrderBadges } from '@/utils/orderBadges';

describe('getOrderBadges', () => {
  it('flags missing delivery date', () => {
    expect(getOrderBadges({ deliveryDate: null }, '2025-08-27')).toEqual(['No date']);
  });

  it('flags overdue orders', () => {
    const badges = getOrderBadges(
      { deliveryDate: '2025-08-25T10:00:00+08:00' },
      '2025-08-27',
    );
    expect(badges).toEqual(['Overdue 2 days']);
  });

  it('returns empty for on-time orders', () => {
    const badges = getOrderBadges(
      { deliveryDate: '2025-08-27T09:00:00+08:00' },
      '2025-08-27',
    );
    expect(badges).toEqual([]);
  });
});


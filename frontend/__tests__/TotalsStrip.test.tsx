import React from 'react';
import { render } from '@testing-library/react';
import TotalsStrip, { Totals } from '@/components/TotalsStrip';

describe('TotalsStrip snapshots', () => {
  const examples: Totals[] = [
    {
      subtotal: 100,
      discount: 0,
      delivery_fee: 10,
      return_delivery_fee: 0,
      penalty_fee: 0,
      total: 110,
      paid_amount: 50,
    },
    {
      subtotal: 200,
      discount: 20,
      delivery_fee: 0,
      return_delivery_fee: 0,
      penalty_fee: 5,
      total: 185,
      paid_amount: 100,
    },
    {
      subtotal: 50,
      discount: 5,
      delivery_fee: 5,
      return_delivery_fee: 5,
      penalty_fee: 10,
      total: 65,
      paid_amount: 65,
    },
  ];

  examples.forEach((order, idx) => {
    it(`renders example ${idx + 1}`, () => {
      const { container } = render(<TotalsStrip order={order} />);
      expect(container.firstChild).toMatchSnapshot();
    });
  });
});

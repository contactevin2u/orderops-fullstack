import React from 'react';

export interface Totals {
  subtotal?: number;
  discount?: number;
  delivery_fee?: number;
  return_delivery_fee?: number;
  penalty_fee?: number;
  total?: number;
  paid_amount?: number;
  balance?: number;
}

const currency = new Intl.NumberFormat('ms-MY', {
  style: 'currency',
  currency: 'MYR',
});

function Money({ amount }: { amount: number }) {
  const parts = currency.formatToParts(amount);
  const symbol = parts.find((p) => p.type === 'currency')?.value || '';
  const number = parts.filter((p) => p.type !== 'currency').map((p) => p.value).join('').trim();
  return (
    <span>
      <span>{symbol}</span> {number}
    </span>
  );
}

export default function TotalsStrip({ order }: { order: Totals }) {
  const {
    subtotal = 0,
    discount = 0,
    delivery_fee = 0,
    return_delivery_fee = 0,
    penalty_fee = 0,
    total = 0,
    paid_amount = 0,
    balance,
  } = order || {};

  const toCollect = balance ?? total - paid_amount;

  const rows = [
    { label: 'Subtotal / Jumlah Kecil', value: subtotal },
    { label: 'Discount / Diskaun', value: -Math.abs(discount) },
    { label: 'Delivery / Penghantaran', value: delivery_fee },
    { label: 'Return Delivery / Pengambilan Balik', value: return_delivery_fee },
    { label: 'Penalty / Denda', value: penalty_fee },
    { label: 'Total / Jumlah', value: total, bold: true },
    { label: 'Paid / Dibayar', value: paid_amount },
    { label: 'To Collect / Baki Perlu Dibayar', value: toCollect, bold: true },
  ];

  return (
    <div className="kv">
      {rows.map((r) => (
        <React.Fragment key={r.label}>
          <div>{r.label}</div>
          <div style={r.bold ? { fontWeight: 600, textAlign: 'right' } : { textAlign: 'right' }}>
            <Money amount={r.value} />
          </div>
        </React.Fragment>
      ))}
    </div>
  );
}


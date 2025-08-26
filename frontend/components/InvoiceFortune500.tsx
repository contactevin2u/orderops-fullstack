"use client";
import React from 'react';

export interface InvoiceItem {
  sku?: string;
  name: string;
  note?: string;
  qty: number;
  unit: string;
  unitPrice: number;
  discount?: number;
  taxRate?: number;
}

export interface InvoiceData {
  brand: {
    logoUrl?: string;
    name: string;
    regNo?: string;
    address?: string;
    phone?: string;
    email?: string;
    website?: string;
    brandColor: string;
  };
  meta: {
    title: string;
    number: string;
    issueDate: string;
    dueDate?: string;
    currency: string;
    taxLabel?: string;
    taxId?: string;
    poNumber?: string;
    reference?: string;
  };
  billTo: {
    label?: string;
    name: string;
    attn?: string;
    address?: string;
    email?: string;
  };
  shipTo?: {
    label?: string;
    name: string;
    attn?: string;
    address?: string;
    email?: string;
  };
  items: InvoiceItem[];
  summary: {
    shipping?: number;
    other?: number;
    rounding?: number;
    depositPaid?: number;
  };
  payment: {
    bankName: string;
    accountName: string;
    accountNo: string;
    swift?: string;
    note?: string;
    qrDataUrl?: string;
  };
  footer: {
    terms: string[];
    note?: string;
  };
}

function shadeColor(color: string, percent: number) {
  const num = parseInt(color.replace('#', ''), 16);
  const amt = Math.round(2.55 * percent);
  const r = (num >> 16) + amt;
  const g = ((num >> 8) & 0x00ff) + amt;
  const b = (num & 0x0000ff) + amt;
  return (
    '#'
    + (
      0x1000000
      + (r < 255 ? (r < 0 ? 0 : r) : 255) * 0x10000
      + (g < 255 ? (g < 0 ? 0 : g) : 255) * 0x100
      + (b < 255 ? (b < 0 ? 0 : b) : 255)
    )
      .toString(16)
      .slice(1)
  );
}

const BRAND_LOGO_URL =
  'https://static.wixstatic.com/media/20c5f7_f890d2de838e43ccb1b30e72b247f0b2~mv2.png';

export default function InvoiceFortune500({ invoice }: { invoice: InvoiceData }) {
  const { brand, meta, billTo, shipTo, items, summary, payment, footer } = invoice;
  const logoUrl = brand.logoUrl || BRAND_LOGO_URL;
  const formatter = new Intl.NumberFormat('en-MY', {
    style: 'currency',
    currency: meta.currency,
  });

  const itemsWithTotals = items.map((it) => {
    const discountedUnit = it.unitPrice * (1 - (it.discount || 0));
    const amount = discountedUnit * it.qty;
    const tax = amount * (it.taxRate || 0);
    return { ...it, amount, tax };
  });
  const subtotal = itemsWithTotals.reduce((s, it) => s + it.amount, 0);
  const taxTotal = itemsWithTotals.reduce((s, it) => s + it.tax, 0);
  const total =
    subtotal +
    taxTotal +
    (summary.shipping || 0) +
    (summary.other || 0) +
    (summary.rounding || 0) -
    (summary.depositPaid || 0);

  const gradientTo = shadeColor(brand.brandColor, 40);

  return (
    <div className="invoice-f500">
      <style jsx>{`
        .invoice-f500 {
          font-family: system-ui, sans-serif;
          font-size: 14px;
          color: #222;
        }
        .brand-bar {
          color: #fff;
          padding: 1rem;
          text-align: center;
          background: linear-gradient(90deg, ${brand.brandColor}, ${gradientTo});
        }
        .brand-details {
          margin-top: 0.5rem;
          font-size: 0.8rem;
        }
        .meta {
          margin: 1rem 0;
        }
        .meta-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
          gap: 0.5rem;
        }
        .billing {
          display: flex;
          gap: 2rem;
          margin-bottom: 1rem;
        }
        .bill-card {
          flex: 1;
          border: 1px solid #ddd;
          padding: 0.5rem;
        }
        table.items {
          width: 100%;
          border-collapse: collapse;
          margin-top: 1rem;
        }
        table.items th,
        table.items td {
          border: 1px solid #ddd;
          padding: 0.5rem;
        }
        table.items th {
          background: #f5f5f5;
          text-align: left;
        }
        table.items td.tabular-nums,
        table.items th.tabular-nums {
          font-variant-numeric: tabular-nums;
          text-align: right;
        }
        .item-note {
          font-size: 0.8rem;
          color: #555;
        }
        .summary {
          margin-top: 1rem;
          width: 50%;
          margin-left: auto;
        }
        .summary-row {
          display: flex;
          justify-content: space-between;
        }
        .summary-row .tabular-nums {
          font-variant-numeric: tabular-nums;
          text-align: right;
        }
        .payment {
          margin-top: 2rem;
          border: 1px solid #ddd;
          padding: 1rem;
        }
        .footer {
          margin-top: 2rem;
        }
        .terms-page {
          page-break-before: always;
          margin-top: 2rem;
        }
        @media print {
          @page {
            size: A4;
            margin: 20mm;
          }
          body {
            background: #fff;
          }
          .terms-page {
            page-break-before: always;
          }
        }
      `}</style>

      <div className="brand-bar">
        <img src={logoUrl} alt={brand.name} style={{ height: '40px' }} />
        <div>{brand.name}</div>
        {brand.regNo && <div className="brand-details">{brand.regNo}</div>}
        {brand.address && <div className="brand-details">{brand.address}</div>}
        {brand.phone && <div className="brand-details">{brand.phone}</div>}
        {brand.email && <div className="brand-details">{brand.email}</div>}
        {brand.website && <div className="brand-details">{brand.website}</div>}
      </div>

      <div className="meta">
        <h1>{meta.title}</h1>
        <div className="meta-grid">
          <div>Invoice #: {meta.number}</div>
          <div>Issue Date: {meta.issueDate}</div>
          {meta.dueDate && <div>Due Date: {meta.dueDate}</div>}
          {meta.poNumber && <div>PO: {meta.poNumber}</div>}
          {meta.reference && <div>Ref: {meta.reference}</div>}
          {meta.taxId && <div>{meta.taxId}</div>}
        </div>
      </div>

      <div className="billing">
        <div className="bill-card">
          <h3>{billTo.label || 'Bill To'}</h3>
          <p>
            {billTo.name}
            {billTo.attn && (
              <>
                <br />
                Attn: {billTo.attn}
              </>
            )}
            {billTo.address && (
              <>
                <br />
                {billTo.address}
              </>
            )}
            {billTo.email && (
              <>
                <br />
                {billTo.email}
              </>
            )}
          </p>
        </div>
        {shipTo && (
          <div className="bill-card">
            <h3>{shipTo.label || 'Ship To'}</h3>
            <p>
              {shipTo.name}
              {shipTo.attn && (
                <>
                  <br />
                  Attn: {shipTo.attn}
                </>
              )}
              {shipTo.address && (
                <>
                  <br />
                  {shipTo.address}
                </>
              )}
              {shipTo.email && (
                <>
                  <br />
                  {shipTo.email}
                </>
              )}
            </p>
          </div>
        )}
      </div>

      <table className="items">
        <thead>
          <tr>
            <th>SKU</th>
            <th>Description</th>
            <th className="tabular-nums">Qty</th>
            <th>Unit</th>
            <th className="tabular-nums">Unit Price</th>
            <th className="tabular-nums">Disc</th>
            <th className="tabular-nums">{meta.taxLabel || 'Tax'}</th>
            <th className="tabular-nums">Amount</th>
          </tr>
        </thead>
        <tbody>
          {itemsWithTotals.map((it, idx) => (
            <tr key={idx}>
              <td>{it.sku}</td>
              <td>
                {it.name}
                {it.note && <div className="item-note">{it.note}</div>}
              </td>
              <td className="tabular-nums">{it.qty}</td>
              <td>{it.unit}</td>
              <td className="tabular-nums">{formatter.format(it.unitPrice)}</td>
              <td className="tabular-nums">
                {it.discount ? `${(it.discount * 100).toFixed(0)}%` : '-'}
              </td>
              <td className="tabular-nums">
                {it.taxRate ? `${(it.taxRate * 100).toFixed(0)}%` : '-'}
              </td>
              <td className="tabular-nums">{formatter.format(it.amount)}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="summary">
        <div className="summary-row">
          <div>Subtotal</div>
          <div className="tabular-nums">{formatter.format(subtotal)}</div>
        </div>
        <div className="summary-row">
          <div>{meta.taxLabel || 'Tax'}</div>
          <div className="tabular-nums">{formatter.format(taxTotal)}</div>
        </div>
        {summary.shipping ? (
          <div className="summary-row">
            <div>Shipping</div>
            <div className="tabular-nums">{formatter.format(summary.shipping)}</div>
          </div>
        ) : null}
        {summary.other ? (
          <div className="summary-row">
            <div>Other</div>
            <div className="tabular-nums">{formatter.format(summary.other)}</div>
          </div>
        ) : null}
        {summary.rounding ? (
          <div className="summary-row">
            <div>Rounding</div>
            <div className="tabular-nums">{formatter.format(summary.rounding)}</div>
          </div>
        ) : null}
        {summary.depositPaid ? (
          <div className="summary-row">
            <div>Deposit Paid</div>
            <div className="tabular-nums">-{formatter.format(summary.depositPaid)}</div>
          </div>
        ) : null}
        <div className="summary-row">
          <div>Total</div>
          <div className="tabular-nums">{formatter.format(total)}</div>
        </div>
      </div>

      <div className="payment">
        <h3>Payment</h3>
        <p>
          {payment.bankName}
          <br />
          {payment.accountName}
          <br />
          {payment.accountNo}
          {payment.swift && (
            <>
              <br />
              SWIFT: {payment.swift}
            </>
          )}
          {payment.note && (
            <>
              <br />
              {payment.note}
            </>
          )}
        </p>
        {payment.qrDataUrl ? (
          <img
            src={payment.qrDataUrl}
            alt="Payment QR code"
            style={{ marginTop: '1rem', height: '120px' }}
          />
        ) : (
          <div
            style={{
              marginTop: '1rem',
              height: '120px',
              width: '120px',
              border: '2px dashed #ddd',
            }}
          />
        )}
      </div>

      <footer className="footer">
        <ul>
          {footer.terms.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
        {footer.note && <p>{footer.note}</p>}
      </footer>

      <div className="terms-page">
        <h2>Terms &amp; Conditions</h2>
        <ul>
          {footer.terms.map((t, i) => (
            <li key={i}>{t}</li>
          ))}
        </ul>
      </div>
    </div>
  );
}


import { InvoiceData } from '@/components/InvoiceFortune500';

export const sampleInvoice: InvoiceData = {
  brand: {
    logoUrl: 'https://static.wixstatic.com/media/20c5f7_f890d2de838e43ccb1b30e72b247f0b2~mv2.png',
    name: 'Acme Sdn Bhd',
    regNo: '202401012345 (1257893-M)',
    address: '123 Jalan Bukit Bintang, 55100 Kuala Lumpur, Malaysia',
    phone: '+60 3-1234 5678',
    email: 'info@acme.my',
    website: 'www.acme.my',
    brandColor: '#2563eb',
  },
  meta: {
    title: 'Tax Invoice',
    number: 'INV-2024-001',
    issueDate: '2024-06-01',
    dueDate: '2024-06-15',
    currency: 'MYR',
    taxLabel: 'SST 6%',
    taxId: 'B16-1234-56789012',
    poNumber: 'PO-2024-02',
    reference: 'REF-2024-06-01',
  },
  billTo: {
    label: 'Bill To',
    name: 'Beta Retail Sdn Bhd',
    attn: 'Finance Department',
    address: '88 Jalan Ampang, 50450 Kuala Lumpur, Malaysia',
    email: 'billing@betaretail.my',
  },
  shipTo: {
    label: 'Ship To',
    name: 'Beta Retail Warehouse',
    address: 'Lot 5, Jalan Klang Lama, 58000 Kuala Lumpur, Malaysia',
  },
  items: [
    {
      sku: 'SKU-1000',
      name: 'Point of Sale System',
      qty: 1,
      unit: 'set',
      unitPrice: 5000,
      taxRate: 0.06,
    },
    {
      sku: 'SKU-1001',
      name: 'Maintenance Service',
      qty: 12,
      unit: 'month',
      unitPrice: 200,
      taxRate: 0.06,
    },
  ],
  summary: {
    shipping: 0,
    other: 0,
    rounding: 0,
    depositPaid: 0,
  },
  payment: {
    bankName: 'Maybank',
    accountName: 'Acme Sdn Bhd',
    accountNo: '512345678901',
    swift: 'MBBEMYKL',
    note: 'Payment due within 14 days.',
  },
  footer: {
    terms: [
      'Goods sold are non-refundable.',
      'Please remit payment to the account stated above.',
    ],
    note: 'Thank you for your business.',
  },
};

export default sampleInvoice;

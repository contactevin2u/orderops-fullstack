import InvoiceFortune500 from '@/components/InvoiceFortune500';
import { sampleInvoice } from '@/lib/sampleInvoice';

export default function InvoicePrintPage({ params }: { params: { id: string } }) {
  const data = { ...sampleInvoice, meta: { ...sampleInvoice.meta, number: params.id } };
  return <InvoiceFortune500 data={data} />;
}

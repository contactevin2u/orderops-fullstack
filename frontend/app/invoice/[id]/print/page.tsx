"use client";

import { useParams } from "next/navigation";

export default function InvoicePrintPage() {
  const params = useParams<{ id: string }>();
  if (!params) return null;
  const { id } = params;

  return (
    <iframe
      src={`/_api/orders/${id}/invoice.pdf`}
      className="fixed inset-0 block w-full h-full border-0"
      title="Invoice PDF"
    />
  );
}

"use client";

import { useParams } from "next/navigation";

export default function InvoicePreviewPage() {
  const params = useParams<{ id: string }>();
  if (!params) return null;
  const { id } = params;

  return (
    <iframe
      src={`/_api/orders/${id}/invoice.pdf`}
      className="fixed inset-0 w-screen h-screen border-0"
    />
  );
}

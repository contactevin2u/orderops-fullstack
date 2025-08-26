"use client";

import { useParams } from "next/navigation";

export default function InvoicePrintPage() {
  const params = useParams<{ id: string }>();
  if (!params) return null;
  const { id } = params;

  return (
    <iframe
      src={`/_api/orders/${id}/invoice.pdf`}
      className="w-full h-screen"
    />
  );
}

"use client";

import { useParams } from "next/navigation";

export default function InvoicePrintPage() {
  const { id } = useParams<{ id: string }>();
  return (
    <iframe
      src={`/_api/orders/${id}/invoice.pdf`}
      className="w-full h-screen"
    />
  );
}

"use client";
import { useParams } from "next/navigation";

export default function InvoicePrintPage() {
  const params = useParams<{ id: string }>();
  if (!params) return null;
  const { id } = params;
  
  return (
    <>
      <style jsx global>{`
        body, html {
          margin: 0 !important;
          padding: 0 !important;
          overflow: hidden !important;
        }
      `}</style>
      <iframe
        src={`/_api/orders/${id}/invoice.pdf`}
        style={{
          position: 'fixed',
          top: 0,
          left: 0,
          width: '100vw',
          height: '100vh',
          border: 'none',
          zIndex: 9999
        }}
      />
    </>
  );
}

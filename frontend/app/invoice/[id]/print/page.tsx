"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import InvoiceFortune500 from "@/components/InvoiceFortune500";

// TODO: replace `any` with actual Order type
type Order = any;

export default function InvoicePrintPage() {
  const params = useParams<{ id: string }>();
  const id = params?.id as string;

  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      try {
        const res = await fetch(`/_api/orders/${id}`, {
          credentials: "include",
          cache: "no-store",
        });
        if (!res.ok) {
          setError(res.statusText);
          return;
        }
        const data: Order = await res.json();
        setOrder(data);
        // window.print();
      } catch (err) {
        setError((err as Error).message);
      }
    }
    if (id) {
      load();
    }
  }, [id]);

  if (error) {
    return (
      <div className="p-4 text-red-500">
        {error}
        <div>
          <Link href={`/invoice/${id}`}>Back to invoice</Link>
        </div>
      </div>
    );
  }

  if (!order) {
    return <div className="p-4">Loading invoice…</div>;
  }

  return (
    <div className="p-4">
      {/* @ts-expect-error Invoice component expects different props */}
      <InvoiceFortune500 order={order} printMode />
    </div>
  );
}


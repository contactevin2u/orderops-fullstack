import * as React from "react";
import useSWR from "swr";
import Link from "next/link";
import { Page, PageHeader } from "@/components/ops/Page";
import { Toolbar } from "@/components/ops/Toolbar";
import StatusPill from "@/components/ops/StatusPill";
import OrderActions from "@/components/ops/OrderActions";
import { Button } from "@/components/ui/button";
import { listOrders } from "@/lib/api";

export default function OpsOrdersPage() {
  const { data, mutate } = useSWR("ops-orders", () => listOrders(undefined, undefined, undefined, 50));
  const orders = data?.items || [];

  return (
    <Page>
      <PageHeader title="Orders" />
      <Toolbar>
        <Button variant="secondary" onClick={() => mutate()}>Refresh</Button>
      </Toolbar>
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead>
            <tr>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">Customer</th>
              <th className="px-3 py-2 text-left">Status</th>
              <th className="px-3 py-2"></th>
            </tr>
          </thead>
          <tbody>
            {orders.map((o: any) => (
              <tr key={o.id} className="divide-x divide-gray-100">
                <td className="px-3 py-2">
                  <Link href={`/ops/${o.id}`} className="underline">
                    {o.code || o.id}
                  </Link>
                </td>
                <td className="px-3 py-2">{o.customer_name || '-'}</td>
                <td className="px-3 py-2"><StatusPill status={o.status} /></td>
                <td className="px-3 py-2">
                  <OrderActions
                    onRecordPayment={() => {}}
                    onReturnCollect={() => {}}
                    onCancelInstalment={() => {}}
                    onBuyback={() => {}}
                    onMarkDone={() => {}}
                  />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Page>
  );
}

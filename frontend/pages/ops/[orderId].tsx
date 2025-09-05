import * as React from "react";
import { useRouter } from "next/router";
import useSWR from "swr";
import { Page, PageHeader } from "@/components/ops/Page";
import StatusPill from "@/components/ops/StatusPill";
import OrderActions from "@/components/ops/OrderActions";
import { getOrder } from "@/lib/api";

export default function OrderDetailPage() {
  const router = useRouter();
  const { orderId } = router.query;
  const { data: order } = useSWR(orderId ? ["order", orderId] : null, () => getOrder(orderId as string));

  if (!order) return null;

  return (
    <Page>
      <PageHeader title={`Order ${order.code || order.id}`} />
      <div className="flex items-center gap-2">
        <StatusPill status={order.status} />
      </div>
      <OrderActions
        onRecordPayment={() => {}}
        onReturnCollect={() => {}}
        onCancelInstalment={() => {}}
        onBuyback={() => {}}
        onMarkDone={() => {}}
      />
    </Page>
  );
}

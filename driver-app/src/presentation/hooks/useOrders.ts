import { useState } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Order, OrderStatus } from "../../core/entities/Order";
import {
  updateStatus as repoUpdateStatus,
  uploadProofOfDelivery as repoUploadProof,
} from "@infra/api/OrderRepository";

const seed: Order[] = [
  {
    id: 1,
    code: "A1",
    status: OrderStatus.ASSIGNED,
    deliveryDate: "2024-01-01",
    customer: { id: 1, name: "Alice", phone: "123", address: "123 Street" },
    pricing: { total_cents: 0 },
  },
  {
    id: 2,
    code: "B2",
    status: OrderStatus.DELIVERED,
    deliveryDate: "2024-01-02",
    customer: { id: 2, name: "Bob", phone: "456", address: "456 Avenue" },
    pricing: { total_cents: 0 },
  },
];

export function useOrders() {
  const [orders] = useState(seed);
  const active = orders.filter((o) => o.status !== OrderStatus.DELIVERED);
  const completed = orders.filter((o) => o.status === OrderStatus.DELIVERED);
  return { active, completed };
}

export function useOrderMutations() {
  const queryClient = useQueryClient();
  const invalidate = () => {
    try {
      queryClient.invalidateQueries({ queryKey: ["orders"] });
    } catch {
      // TODO: provide QueryClient for invalidation
    }
  };

  const updateStatus = async (id: number | string, status: string) => {
    await repoUpdateStatus(id, status);
    invalidate();
  };

  const uploadProofOfDelivery = async (id: number | string, uri: string) => {
    await repoUploadProof(id, uri);
    invalidate();
  };

  return { updateStatus, uploadProofOfDelivery };
}

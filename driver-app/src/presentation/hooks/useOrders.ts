import { useState } from "react";
import { Order, OrderStatus } from "../../core/entities/Order";

const seed: Order[] = [
  {
    id: 1,
    status: OrderStatus.ASSIGNED,
    customer: { id: 1, name: "Alice", phone: "123", address: "123 Street" },
  },
  {
    id: 2,
    status: OrderStatus.DELIVERED,
    customer: { id: 2, name: "Bob", phone: "456", address: "456 Avenue" },
  },
];

export function useOrders() {
  const [orders] = useState(seed);
  const active = orders.filter((o) => o.status !== OrderStatus.DELIVERED);
  const completed = orders.filter((o) => o.status === OrderStatus.DELIVERED);
  return { active, completed };
}

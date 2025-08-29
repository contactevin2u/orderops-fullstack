import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import * as orderRepo from "@infra/api/OrderRepository";
import { OrderStatus } from "@core/entities/Order";

export function useOrders(repo = orderRepo) {
  const qc = useQueryClient();
  const {
    data: orders = [],
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: ["orders"],
    queryFn: repo.getAll,
    staleTime: 30_000,
  });

  const startDelivery = useMutation({
    mutationFn: (id: number) => repo.updateStatus(id, OrderStatus.IN_TRANSIT),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });

  const holdDelivery = useMutation({
    mutationFn: (id: number) => repo.updateStatus(id, OrderStatus.ON_HOLD),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });

  const resumeDelivery = useMutation({
    mutationFn: (id: number) => repo.updateStatus(id, OrderStatus.IN_TRANSIT),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });

  const completeDelivery = useMutation({
    mutationFn: async ({ id, proofUri }: { id: number; proofUri: string }) => {
      await repo.uploadProofOfDelivery(id, proofUri);
      await repo.updateStatus(id, OrderStatus.DELIVERED);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["orders"] }),
  });

  const active = orders.filter((o) => o.status !== OrderStatus.DELIVERED);
  const completed = orders.filter((o) => o.status === OrderStatus.DELIVERED);

  return {
    activeOrders: active,
    completedOrders: completed,
    loading: isLoading,
    error,
    refresh: refetch,
    startDelivery,
    holdDelivery,
    resumeDelivery,
    completeDelivery,
  };
}

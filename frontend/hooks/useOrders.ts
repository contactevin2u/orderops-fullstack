import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import * as api from '@/lib/api';

export function useOrders(filters?: {
  q?: string;
  status?: string;
  date?: string;
  driver_id?: number;
  unassigned?: boolean;
}) {
  return useQuery({
    queryKey: ['orders', filters],
    queryFn: () => api.listOrders(
      filters?.q,
      filters?.status,
      undefined,
      undefined,
      filters
    ),
  });
}

export function useOrder(id: number) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => api.getOrder(id),
    enabled: !!id,
  });
}

export function useCreateOrder() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: api.createManualOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useUpdateOrder() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: any }) => api.updateOrder(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['order', id] });
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useDeleteOrder() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: api.voidOrder,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    },
  });
}

export function useOrderDue(id: number) {
  return useQuery({
    queryKey: ['order-due', id],
    queryFn: () => api.orderDue(id),
    enabled: !!id,
  });
}
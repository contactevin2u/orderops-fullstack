import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDrivers, createDriver, fetchDriver, updateDriver } from '@/lib/api';
import type { DriverCreateForm, DriverUpdateForm } from '@/lib/zod-schemas';

export function useDrivers() {
  return useQuery({
    queryKey: ['drivers'],
    queryFn: listDrivers,
  });
}

export function useDriver(id: number) {
  return useQuery({
    queryKey: ['driver', id],
    queryFn: () => fetchDriver(id),
    enabled: !!id,
  });
}

export function useCreateDriver() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (data: DriverCreateForm) => createDriver(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['drivers'] });
    },
  });
}

export function useUpdateDriver() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: DriverUpdateForm }) => updateDriver(id, data),
    onSuccess: (_, { id }) => {
      queryClient.invalidateQueries({ queryKey: ['driver', id] });
      queryClient.invalidateQueries({ queryKey: ['drivers'] });
    },
  });
}
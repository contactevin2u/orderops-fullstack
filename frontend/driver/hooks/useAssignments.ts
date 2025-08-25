import React from 'react';
import useSWR from 'swr';
import { fetchDriverAssignments } from '@/utils/api';

export default function useAssignments(date?: string) {
  const { data, error, isLoading, mutate } = useSWR(
    ['driver-assignments', date],
    () => fetchDriverAssignments(date)
  );

  return {
    data,
    isLoading,
    error,
    refetch: mutate,
  };
}

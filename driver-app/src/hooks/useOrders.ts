import { useCallback, useEffect, useRef, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { useOrderStore, Order } from '../stores/orderStore';
import { api } from '../lib/api';
import { useAuth } from './useAuth';

interface Options {
  skipPolling?: boolean;
}

export function useOrders(options?: Options) {
  const { idToken } = useAuth();
  const orders = useOrderStore((s) => s.orders);
  const setOrders = useOrderStore((s) => s.setOrders);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  const refresh = useCallback(async () => {
    if (!idToken) return;
    setLoading(true);
    setError(null);
    const res = await api.get('/drivers/orders', idToken);
    if (res.ok) {
      setOrders(res.data?.data ?? res.data ?? []);
    } else {
      setError(res.error || String(res.status));
    }
    setLoading(false);
  }, [idToken, setOrders]);

  const update = useCallback(
    async (id: number, status: string) => {
      if (!idToken) return;
      setOrders((prev) => prev.map((o) => (o.id === id ? { ...o, status } : o)));
      const res = await api.patch(`/drivers/orders/${id}`, idToken, { status });
      if (!res.ok) refresh();
    },
    [idToken, setOrders, refresh],
  );

  const completeWithPhoto = useCallback(
    async (id: number) => {
      if (!idToken) return;
      const res = await ImagePicker.launchCameraAsync({ allowsEditing: false, quality: 0.7 });
      if (res.canceled) return;
      const asset = res.assets[0];
      const manip = await ImageManipulator.manipulateAsync(
        asset.uri,
        [{ resize: { width: 1280 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG },
      );
      const form = new FormData();
      form.append('file', { uri: manip.uri, type: 'image/jpeg', name: 'pod.jpg' } as any);
      await api.upload(`/drivers/orders/${id}/pod-photo`, idToken, form);
      await update(id, 'DELIVERED');
    },
    [idToken, update],
  );

  const pendingCount = orders.filter((o) => o.status !== 'DELIVERED').length;

  useEffect(() => {
    if (options?.skipPolling || !idToken) return;
    refresh();
    if (!timerRef.current) {
      timerRef.current = setInterval(refresh, 20 * 60 * 1000);
    }
    return () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [idToken, refresh, options?.skipPolling]);

  return { orders, loading, error, refresh, update, completeWithPhoto, pendingCount };
}

import { useCallback, useEffect, useRef, useState } from 'react';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
import { AppState } from 'react-native';
import { useOrderStore } from '../stores/orderStore';
import { api } from '../lib/api';
import { toast } from '../components/Toast';
import { useNetwork } from './useNetwork';
import { useOutbox } from '../offline/useOutbox';
import { OutboxJob } from '../offline/types';

const uuid = () => (globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : Math.random().toString(36).slice(2));

interface Options {
  skipPolling?: boolean;
}

function formFromEntries(entries: [string, any][]) {
  const f = new FormData();
  entries.forEach(([k, v]) => f.append(k, v as any));
  return f;
}

export function useOrders(options?: Options) {
  const orders = useOrderStore((s) => s.orders);
  const setOrders = useOrderStore((s) => s.setOrders);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<NodeJS.Timeout | null>(null);
  const { online } = useNetwork();
  const { enqueue, syncing, lastSyncAt } = useOutbox();

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    const res = await api.get('/drivers/orders');
    if (res.ok) {
      setOrders(res.data?.data ?? res.data ?? []);
    } else {
      setError(res.error || String(res.status));
    }
    setLoading(false);
  }, [setOrders]);

  const enqueuePatch = useCallback(
    async (id: number, status: string) => {
      const job: OutboxJob = {
        id: uuid(),
        createdAt: Date.now(),
        attempts: 0,
        kind: 'PATCH',
        url: `/drivers/orders/${id}`,
        bodyType: 'json',
        body: { status },
      };
      await enqueue(job);
    },
    [enqueue],
  );

  const update = useCallback(
    async (id: number, status: string) => {
      setOrders((prev) => prev.map((o) => (o.id === id ? { ...o, status } : o)));
      if (!online) {
        await enqueuePatch(id, status);
        toast.show('Queued. Will send when back online.');
        return;
      }
      const res = await api.patch(`/drivers/orders/${id}`, { status });
      if (!res.ok) {
        await enqueuePatch(id, status);
        toast.show(res.error || 'Failed to update. Will retry.', 'error');
      }
    },
    [online, setOrders, enqueuePatch],
  );

  const completeWithPhoto = useCallback(
    async (id: number) => {
      const res = await ImagePicker.launchCameraAsync({ allowsEditing: false, quality: 0.7 });
      if (res.canceled) return;
      const asset = res.assets[0];
      const manip = await ImageManipulator.manipulateAsync(
        asset.uri,
        [{ resize: { width: 1280 } }],
        { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG },
      );
      const entries: [string, any][] = [
        ['file', { uri: manip.uri, type: 'image/jpeg', name: 'pod.jpg' }],
      ];
      const uploadJob: OutboxJob = {
        id: uuid(),
        createdAt: Date.now(),
        attempts: 0,
        kind: 'UPLOAD',
        url: `/drivers/orders/${id}/pod-photo`,
        bodyType: 'formdata',
        body: entries,
      };
      const patchJob: OutboxJob = {
        id: uuid(),
        createdAt: Date.now(),
        attempts: 0,
        kind: 'PATCH',
        url: `/drivers/orders/${id}`,
        bodyType: 'json',
        body: { status: 'DELIVERED' },
      };

      if (!online) {
        setOrders((prev) => prev.map((o) => (o.id === id ? { ...o, podPending: true } : o)));
        await enqueue(uploadJob);
        await enqueue(patchJob);
        toast.show('PoD upload queued. Will sync when back online.', 'info');
        return;
      }

      const uploadRes = await api.upload(`/drivers/orders/${id}/pod-photo`, formFromEntries(entries));
      if (!uploadRes.ok) {
        if (uploadRes.status === 400 && uploadRes.error?.includes('PoD photo required')) {
          toast.show('Proof of Delivery is required.', 'error');
          return;
        }
        setOrders((prev) => prev.map((o) => (o.id === id ? { ...o, podPending: true } : o)));
        await enqueue(uploadJob);
        await enqueue(patchJob);
        toast.show('PoD upload queued. Will sync when online.', 'info');
        return;
      }

      const patchRes = await api.patch(`/drivers/orders/${id}`, { status: 'DELIVERED' });
      if (!patchRes.ok) {
        await enqueue(patchJob);
        toast.show(patchRes.error || 'Failed to update. Will retry.', 'error');
      } else {
        setOrders((prev) =>
          prev.map((o) => (o.id === id ? { ...o, status: 'DELIVERED', podPending: false } : o)),
        );
      }
    },
    [online, enqueue, setOrders],
  );

  const pendingCount = orders.filter((o) => o.status !== 'DELIVERED').length;

  useEffect(() => {
    if (options?.skipPolling) return;

    const start = () => {
      if (!timerRef.current && AppState.currentState === 'active' && !syncing) {
        refresh();
        timerRef.current = setInterval(refresh, 15 * 60 * 1000);
      }
    };
    const stop = () => {
      if (timerRef.current) {
        clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
    start();
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') start();
      else stop();
    });
    return () => {
      stop();
      sub.remove();
    };
  }, [refresh, options?.skipPolling, syncing]);

  useEffect(() => {
    if (lastSyncAt) refresh();
  }, [lastSyncAt, refresh]);

  return { orders, loading, error, refresh, update, completeWithPhoto, pendingCount };
}


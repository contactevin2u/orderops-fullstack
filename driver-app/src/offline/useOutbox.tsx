import React, { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react';
import { AppState } from 'react-native';
import { api } from '../lib/api';
import { useNetwork } from '../hooks/useNetwork';
import { OutboxJob } from './types';
import { enqueue as persistEnqueue, list, replaceAll, backoff } from './outbox';

interface Ctx {
  enqueue: (job: OutboxJob) => Promise<void>;
  syncing: boolean;
  lastSyncAt: number | null;
  pending: number;
}

const OutboxContext = createContext<Ctx | undefined>(undefined);

function useProvider(): Ctx {
  const { online } = useNetwork();
  const [syncing, setSyncing] = useState(false);
  const [lastSyncAt, setLastSyncAt] = useState<number | null>(null);
  const [pending, setPending] = useState(0);
  const timer = useRef<NodeJS.Timeout | null>(null);

  const send = useCallback(async (job: OutboxJob) => {
    switch (job.kind) {
      case 'PATCH':
        return api.patch(job.url, job.body, job.headers);
      case 'POST':
        return api.post(job.url, job.body, job.headers);
      case 'UPLOAD': {
        const form = new FormData();
        (job.body as [string, any][]).forEach(([k, v]) => form.append(k, v as any));
        return api.upload(job.url, form, job.headers);
      }
      case 'DELETE':
        return api.delete(job.url, job.headers);
      default:
        return { ok: false, status: 0, error: 'unknown job' };
    }
  }, []);

  const flush = useCallback(async () => {
    if (syncing) return;
    const jobs = await list();
    setPending(jobs.length);
    if (!jobs.length) {
      setLastSyncAt(Date.now());
      return;
    }
    setSyncing(true);
    let remaining = jobs;
    for (const job of jobs) {
      const res = await send(job);
      if (res.ok) {
        remaining = remaining.filter((j) => j.id !== job.id);
        await replaceAll(remaining);
        setPending(remaining.length);
      } else {
        job.attempts += 1;
        await replaceAll(remaining);
        const delay = backoff(job.attempts);
        if (timer.current) clearTimeout(timer.current);
        timer.current = setTimeout(() => flush(), delay);
        setSyncing(false);
        return;
      }
    }
    setSyncing(false);
    setLastSyncAt(Date.now());
  }, [send, syncing]);

  useEffect(() => {
    if (online) flush();
  }, [online, flush]);

  useEffect(() => {
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') flush();
    });
    return () => sub.remove();
  }, [flush]);

  const enqueue = useCallback(async (job: OutboxJob) => {
    await persistEnqueue(job);
    const jobs = await list();
    setPending(jobs.length);
    if (online) flush();
  }, [flush, online]);

  useEffect(() => {
    list().then((jobs) => setPending(jobs.length));
  }, []);

  return { enqueue, syncing, lastSyncAt, pending };
}

export const OutboxProvider: React.FC<React.PropsWithChildren> = ({ children }) => {
  const value = useProvider();
  return <OutboxContext.Provider value={value}>{children}</OutboxContext.Provider>;
};

export function useOutbox() {
  const ctx = useContext(OutboxContext);
  if (!ctx) throw new Error('useOutbox must be used within OutboxProvider');
  return ctx;
}


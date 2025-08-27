import AsyncStorage from '@react-native-async-storage/async-storage';
import { OutboxJob } from './types';

const KEY = 'OUTBOX_V1';

let storage: typeof AsyncStorage = AsyncStorage;

export function __setStorage(s: typeof AsyncStorage) {
  storage = s;
}

export async function list(): Promise<OutboxJob[]> {
  const raw = await storage.getItem(KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as OutboxJob[];
  } catch {
    return [];
  }
}

export async function replaceAll(jobs: OutboxJob[]): Promise<void> {
  await storage.setItem(KEY, JSON.stringify(jobs));
}

export async function enqueue(job: OutboxJob): Promise<void> {
  const jobs = await list();
  jobs.push(job);
  await replaceAll(jobs);
}

export function backoff(attempts: number): number {
  const base = 2000; // 2s
  const max = 120000; // 2m
  const exp = Math.min(base * Math.pow(2, attempts), max);
  const jitter = Math.random() * base;
  return exp + jitter;
}


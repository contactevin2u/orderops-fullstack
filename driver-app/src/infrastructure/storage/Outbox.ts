import AsyncStorage from "@react-native-async-storage/async-storage";

export type UpdateStatusJob = {
  type: "UPDATE_STATUS";
  id: string;
  orderId: string;
  payload: { status: string };
  retries: number;
  ts: number;
  lastAttempt?: number;
};

export type UploadPodJob = {
  type: "UPLOAD_POD";
  id: string;
  orderId: string;
  payload: { uri: string };
  retries: number;
  ts: number;
  lastAttempt?: number;
};

export type OutboxJob = UpdateStatusJob | UploadPodJob;

const STORAGE_KEY = "@offline_queue_v1";

async function read(): Promise<OutboxJob[]> {
  const raw = await AsyncStorage.getItem(STORAGE_KEY);
  if (!raw) return [];
  try {
    return JSON.parse(raw) as OutboxJob[];
  } catch {
    return [];
  }
}

async function write(jobs: OutboxJob[]): Promise<void> {
  await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(jobs));
}

export async function enqueue(job: OutboxJob): Promise<void> {
  const jobs = await read();
  jobs.push(job);
  await write(jobs);
}

const BASE = 2000; // ms

export async function getPending(): Promise<OutboxJob[]> {
  const jobs = await read();
  const now = Date.now();
  return jobs.filter((j) => {
    if (j.retries === 0 || !j.lastAttempt) return true;
    const delay = BASE * Math.pow(2, j.retries) + Math.floor(Math.random() * 250);
    return now - j.lastAttempt >= delay;
  });
}

export async function markAttempt(id: string): Promise<void> {
  const jobs = await read();
  const job = jobs.find((j) => j.id === id);
  if (job) {
    job.lastAttempt = Date.now();
    await write(jobs);
  }
}

export async function markCompleted(id: string): Promise<void> {
  const jobs = (await read()).filter((j) => j.id !== id);
  await write(jobs);
}

export async function incrementRetries(id: string): Promise<void> {
  const jobs = await read();
  const updated = jobs.map((j) =>
    j.id === id ? { ...j, retries: j.retries + 1 } : j
  );
  await write(updated);
}

export async function count(): Promise<number> {
  return (await read()).length;
}


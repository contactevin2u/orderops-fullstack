import ApiClient from "./ApiClient";
import {
  enqueue,
  getPending,
  markCompleted,
  incrementRetries,
  OutboxJob,
} from "../storage/Outbox";

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

export async function getAll() {
  return ApiClient.get("/drivers/orders");
}

export async function getById(id: string | number) {
  return ApiClient.get(`/drivers/orders/${id}`);
}

export async function updateStatus(id: string | number, status: string) {
  const jobId = generateId();
  try {
    await ApiClient.patch(
      `/drivers/orders/${id}`,
      { status },
      { idempotencyKey: jobId }
    );
  } catch {
    const job: OutboxJob = {
      type: "UPDATE_STATUS",
      id: jobId,
      orderId: String(id),
      payload: { status },
      retries: 0,
      ts: Date.now(),
    };
    await enqueue(job);
  }
}

export async function uploadProofOfDelivery(id: string | number, uri: string) {
  const jobId = generateId();
  try {
    await ApiClient.upload(
      `/drivers/orders/${id}/pod-photo`,
      uri,
      { idempotencyKey: jobId }
    );
  } catch {
    const job: OutboxJob = {
      type: "UPLOAD_POD",
      id: jobId,
      orderId: String(id),
      payload: { uri },
      retries: 0,
      ts: Date.now(),
    };
    await enqueue(job);
  }
}

export async function syncPendingChanges() {
  const pending = await getPending();
  for (const job of pending) {
    try {
      if (job.type === "UPDATE_STATUS") {
        await ApiClient.patch(
          `/drivers/orders/${job.orderId}`,
          { status: job.payload.status },
          { idempotencyKey: job.id }
        );
      } else {
        await ApiClient.upload(
          `/drivers/orders/${job.orderId}/pod-photo`,
          job.payload.uri,
          { idempotencyKey: job.id }
        );
      }
      await markCompleted(job.id);
    } catch {
      await incrementRetries(job.id);
    }
  }
}


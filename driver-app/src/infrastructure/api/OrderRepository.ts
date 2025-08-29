import ApiClient from "./ApiClient";
import {
  enqueue,
  getPending,
  markAttempt,
  markCompleted,
  incrementRetries,
  OutboxJob,
} from "../storage/Outbox";
import { ApiOrderSchema, ApiOrderListSchema, ApiOrder } from "./schemas";
import { Order } from "@core/entities/Order";

function generateId() {
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

let flushLock: Promise<void> | null = null;

export function mapApiOrder(api: ApiOrder): Order {
  return {
    id: api.id,
    code: api.code,
    status: api.status,
    deliveryDate: api.delivery_date,
    customer: {
      id: api.customer.id,
      name: api.customer.name,
      phone: api.customer.phone,
      address: api.customer.address,
      mapUrl: api.customer.map_url,
    },
    pricing: {
      total_cents: api.pricing.total_cents,
    },
  };
}

export async function getAll(): Promise<Order[]> {
  const json = await ApiClient.get("/drivers/orders");
  const parsed = ApiOrderListSchema.parse(json);
  return parsed.map(mapApiOrder);
}

export async function getById(id: string | number): Promise<Order | null> {
  try {
    const json = await ApiClient.get(`/drivers/orders/${id}`);
    const parsed = ApiOrderSchema.parse(json);
    return mapApiOrder(parsed);
  } catch (err: any) {
    if (err?.status === 404) return null;
    throw err;
  }
}

export async function updateStatus(
  id: string | number,
  status: string,
  invalidate?: () => void
) {
  const jobId = generateId();
  try {
    await ApiClient.patch(
      `/drivers/orders/${id}`,
      { status },
      { idempotencyKey: jobId }
    );
    invalidate?.();
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

export async function uploadProofOfDelivery(
  id: string | number,
  uri: string,
  invalidate?: () => void
) {
  const jobId = generateId();
  try {
    await ApiClient.upload(
      `/drivers/orders/${id}/pod-photo`,
      uri,
      { idempotencyKey: jobId }
    );
    invalidate?.();
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

export async function syncPendingChanges(): Promise<void> {
  if (flushLock) return flushLock;
  flushLock = (async () => {
    try {
      const pending = await getPending();
      for (const job of pending) {
        await markAttempt(job.id);
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
    } finally {
      flushLock = null;
    }
  })();
  return flushLock;
}


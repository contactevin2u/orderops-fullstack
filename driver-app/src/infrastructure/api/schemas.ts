import { z } from 'zod';
import { Order, OrderStatus } from '@core/entities/Order';

export const ApiCustomerSchema = z.object({
  id: z.number(),
  name: z.string(),
  phone: z.string(),
  address: z.string(),
  mapUrl: z.string().optional(),
});

export const ApiOrderSchema = z.object({
  id: z.number(),
  status: z.nativeEnum(OrderStatus),
  customer: ApiCustomerSchema,
});

export type ApiOrder = z.infer<typeof ApiOrderSchema>;

export const ApiOrderListSchema = z.array(ApiOrderSchema);

export function mapOrder(api: ApiOrder): Order {
  return {
    id: api.id,
    status: api.status,
    customer: api.customer,
  };
}

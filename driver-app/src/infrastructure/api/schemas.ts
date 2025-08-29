import { z } from 'zod';
import { OrderStatus } from '@core/entities/Order';

export const ApiCustomerSchema = z.object({
  id: z.number(),
  name: z.string(),
  phone: z.string(),
  address: z.string(),
  map_url: z.string().optional(),
});

export const ApiPricingSchema = z.object({
  total_cents: z.number(),
});

export const ApiOrderSchema = z.object({
  id: z.number(),
  code: z.string(),
  status: z.nativeEnum(OrderStatus),
  delivery_date: z.string(),
  customer: ApiCustomerSchema,
  pricing: ApiPricingSchema,
});

export const ApiOrderListSchema = z.array(ApiOrderSchema);

export type ApiOrder = z.infer<typeof ApiOrderSchema>;
export type ApiOrderList = z.infer<typeof ApiOrderListSchema>;

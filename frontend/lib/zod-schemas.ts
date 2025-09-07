// Form validation schemas using Zod

import { z } from 'zod';

// Common schemas
export const phoneSchema = z.string()
  .optional()
  .refine(val => !val || /^(\+?6)?01[0-9]-?[0-9]{3,4}[-\s]?[0-9]{4}$/.test(val), {
    message: 'Invalid Malaysian phone number format'
  });

export const emailSchema = z.string().email('Invalid email address');

export const currencySchema = z.string()
  .transform(val => parseFloat(val.replace(/[^0-9.-]/g, '')))
  .refine(val => !isNaN(val) && val >= 0, 'Must be a valid positive amount');

export const dateSchema = z.string()
  .optional()
  .refine(val => !val || !isNaN(Date.parse(val)), 'Invalid date format');

// User schemas  
export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(1, 'Password is required'),
});

export const userCreateSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters'),
  email: emailSchema,
  password: z.string().min(6, 'Password must be at least 6 characters'),
  role: z.enum(['ADMIN', 'CASHIER', 'DRIVER']),
});

// Customer schemas
export const customerSchema = z.object({
  name: z.string().min(1, 'Customer name is required'),
  phone: phoneSchema,
  address: z.string().optional(),
  map_url: z.string().url().optional().or(z.literal('')),
});

// Order schemas
export const orderItemSchema = z.object({
  name: z.string().min(1, 'Item name is required'),
  sku: z.string().optional(),
  category: z.enum(['BED', 'WHEELCHAIR', 'OXYGEN', 'ACCESSORY']).optional(),
  item_type: z.enum(['OUTRIGHT', 'INSTALLMENT', 'RENTAL', 'FEE']),
  qty: z.number().min(1, 'Quantity must be at least 1'),
  unit_price: currencySchema,
  line_total: currencySchema,
});

export const planSchema = z.object({
  plan_type: z.enum(['RENTAL', 'INSTALLMENT']),
  months: z.number().min(1).max(60).optional(),
  monthly_amount: currencySchema,
  start_date: dateSchema,
});

export const orderCreateSchema = z.object({
  customer: customerSchema,
  items: z.array(orderItemSchema).min(1, 'At least one item is required'),
  plan: planSchema.optional(),
  delivery_date: dateSchema,
  notes: z.string().optional(),
  delivery_fee: currencySchema.optional(),
  return_delivery_fee: currencySchema.optional(),
  penalty_fee: currencySchema.optional(),
  discount: currencySchema.optional(),
});

// Payment schemas
export const paymentSchema = z.object({
  amount: currencySchema.refine(val => val > 0, 'Amount must be greater than 0'),
  method: z.enum(['CASH', 'TRANSFER', 'CHEQUE', 'CARD', 'ONLINE']),
  reference: z.string().optional(),
  date: dateSchema,
  notes: z.string().optional(),
});

// Driver schemas
export const driverCreateSchema = z.object({
  email: emailSchema,
  password: z.string().min(6, 'Password must be at least 6 characters'),
  name: z.string().min(1, 'Driver name is required'),
  phone: phoneSchema,
  base_warehouse: z.enum(['BATU_CAVES', 'KOTA_KINABALU']),
  firebase_uid: z.string().optional(),
});

export const driverUpdateSchema = z.object({
  name: z.string().min(1, 'Driver name is required'),
  phone: phoneSchema,
  base_warehouse: z.enum(['BATU_CAVES', 'KOTA_KINABALU']),
});

// Route schemas
export const routeCreateSchema = z.object({
  driver_id: z.number(),
  route_date: z.string().refine(val => !isNaN(Date.parse(val)), 'Invalid date'),
  name: z.string().min(1, 'Route name is required'),
  notes: z.string().optional(),
});

// Export types
export type LoginForm = z.infer<typeof loginSchema>;
export type UserCreateForm = z.infer<typeof userCreateSchema>;
export type CustomerForm = z.infer<typeof customerSchema>;
export type OrderItemForm = z.infer<typeof orderItemSchema>;
export type PlanForm = z.infer<typeof planSchema>;
export type OrderCreateForm = z.infer<typeof orderCreateSchema>;
export type PaymentForm = z.infer<typeof paymentSchema>;
export type DriverCreateForm = z.infer<typeof driverCreateSchema>;
export type DriverUpdateForm = z.infer<typeof driverUpdateSchema>;
export type RouteCreateForm = z.infer<typeof routeCreateSchema>;
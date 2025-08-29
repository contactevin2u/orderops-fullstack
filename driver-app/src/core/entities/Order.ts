export type ISODateString = string;
export type Cents = number;

export enum OrderStatus {
  ASSIGNED = "ASSIGNED",
  IN_TRANSIT = "IN_TRANSIT",
  ON_HOLD = "ON_HOLD",
  DELIVERED = "DELIVERED",
  CANCELLED = "CANCELLED",
}

export interface Customer {
  id: number;
  name: string;
  phone: string;
  address: string;
  mapUrl?: string;
}

export interface Order {
  id: number;
  code: string;
  status: OrderStatus;
  deliveryDate: ISODateString;
  customer: Customer;
  pricing: {
    total_cents: Cents;
  };
}

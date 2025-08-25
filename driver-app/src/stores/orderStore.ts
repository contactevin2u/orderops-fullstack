import create from 'zustand';

export interface Customer {
  id?: number;
  name?: string;
  phone?: string;
  address?: string;
  map_url?: string;
}

export interface OrderItem {
  id: number;
  name: string;
  qty: number;
  unit_price?: number;
  line_total?: number;
  item_type?: string;
}

export interface Order {
  id: number;
  description?: string;    // compat
  code?: string;           // new explicit order code
  status: string;

  delivery_date?: string;
  notes?: string;
  customer?: Customer;

  subtotal?: number;
  discount?: number;
  delivery_fee?: number;
  return_delivery_fee?: number;
  penalty_fee?: number;
  total?: number;
  paid_amount?: number;
  balance?: number;

  items?: OrderItem[];
}

interface OrderState {
  orders: Order[];
  setOrders: (orders: Order[]) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  orders: [],
  setOrders: (orders) => set({ orders }),
}));

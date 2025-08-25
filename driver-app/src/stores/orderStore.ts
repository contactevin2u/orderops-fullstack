import create from 'zustand';

export interface OrderItem {
  id: number;
  name: string;
  qty: number;
}

export interface Order {
  id: number;
  description: string;
  status: string;
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

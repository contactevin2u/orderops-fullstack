import create from 'zustand';

export interface Order {
  id: number;
  description: string;
  status: string;
}

interface OrderState {
  orders: Order[];
  setOrders: (orders: Order[]) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  orders: [],
  setOrders: (orders) => set({ orders }),
}));

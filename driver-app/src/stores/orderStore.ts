import create from 'zustand';

export interface Order {
  id: string;
  description: string;
  assignedDrivers: string[]; // one or two driver IDs
  initialPayment: number; // payment collected at start
  commissionRate: number; // 0.1 means 10%
  status: 'assigned' | 'completed';
  photoUrl?: string; // proof-of-delivery photo
}

interface OrderState {
  orders: Order[];
  assignOrder: (order: Order) => void;
  completeOrder: (id: string, photoUrl: string) => void;
}

export const useOrderStore = create<OrderState>((set) => ({
  // demo data; in real app this would come from API
  orders: [
    {
      id: '1',
      description: 'Deliver documents to ABC Corp',
      assignedDrivers: ['driver1', 'driver2'],
      initialPayment: 100,
      commissionRate: 0.15,
      status: 'assigned',
    },
  ],
  assignOrder: (order) =>
    set((state) => ({ orders: [...state.orders, order] })),
  completeOrder: (id, photoUrl) =>
    set((state) => ({
      orders: state.orders.map((o) =>
        o.id === id ? { ...o, status: 'completed', photoUrl } : o
      ),
    })),
}));

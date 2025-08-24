import create from 'zustand';
import Constants from 'expo-constants';

const API_BASE =
  (Constants?.expoConfig?.extra as any)?.apiBase ||
  'https://orderops-api-v1.onrender.com';

export interface Trip {
  id: number;
  order_id: number;
  status: string;
  pod_photo_url?: string | null;
}

interface TripState {
  trips: Trip[];
  load: (token: string) => Promise<void>;
  updateStatus: (
    token: string,
    id: number,
    action: 'start' | 'deliver' | 'fail',
    photoUri?: string
  ) => Promise<void>;
}

export const useTripStore = create<TripState>((set, get) => ({
  trips: [],
  load: async (token: string) => {
    try {
      const res = await fetch(`${API_BASE}/trips/active`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const json = await res.json();
      const data = Array.isArray(json.data) ? json.data : [];
      set({ trips: data });
    } catch (e) {
      console.error('load trips failed', e);
    }
  },
  updateStatus: async (token, id, action, photoUri) => {
    try {
      const url = `${API_BASE}/trips/${id}/${action}`;
      const headers: any = { Authorization: `Bearer ${token}` };
      let body: any;
      if (photoUri) {
        const fd = new FormData();
        fd.append('photo', {
          uri: photoUri,
          name: 'pod.jpg',
          type: 'image/jpeg',
        } as any);
        body = fd;
      }
      await fetch(url, { method: 'POST', headers, body });
      await get().load(token);
    } catch (e) {
      console.error('update status failed', e);
    }
  },
}));

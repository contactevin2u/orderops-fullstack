export type Listener<T = any> = (payload: T) => void;

const listeners = new Map<string, Set<Listener>>();

export function on<T = any>(event: string, listener: Listener<T>) {
  if (!listeners.has(event)) {
    listeners.set(event, new Set());
  }
  listeners.get(event)!.add(listener as Listener);
  return () => off(event, listener);
}

export function off(event: string, listener: Listener) {
  const set = listeners.get(event);
  if (!set) return;
  set.delete(listener);
  if (set.size === 0) listeners.delete(event);
}

export function emit<T = any>(event: string, payload: T) {
  const set = listeners.get(event);
  if (!set) return;
  for (const listener of Array.from(set)) {
    listener(payload);
  }
}

export const ORDER_OPEN_EVENT = 'order:open';

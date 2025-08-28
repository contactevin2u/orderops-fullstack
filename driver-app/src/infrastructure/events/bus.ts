type Listener = (payload: any) => void;

const listeners = new Map<string, Set<Listener>>();

export function on(event: string, fn: Listener) {
  if (!listeners.has(event)) {
    listeners.set(event, new Set());
  }
  listeners.get(event)!.add(fn);
  return () => off(event, fn);
}

export function off(event: string, fn: Listener) {
  const set = listeners.get(event);
  if (!set) return;
  set.delete(fn);
  if (set.size === 0) listeners.delete(event);
}

export function emit(event: string, payload: any) {
  const set = listeners.get(event);
  if (!set) return;
  for (const fn of set) {
    fn(payload);
  }
}

export const ORDER_OPEN_EVENT = 'order:open';

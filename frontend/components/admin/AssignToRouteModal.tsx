import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRoutes, assignOrdersToRoute } from '@/utils/apiAdapter';

interface Props {
  orderIds: string[];
  date: string;
  onClose: () => void;
}

export default function AssignToRouteModal({ orderIds, date, onClose }: Props) {
  const { data: routes, isLoading, isError } = useQuery({
    queryKey: ['routes', date],
    queryFn: () => fetchRoutes(date),
  });
  const qc = useQueryClient();
  const [routeId, setRouteId] = useState('');

  const mutation = useMutation({
    mutationFn: () => assignOrdersToRoute(routeId, orderIds),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routes', date] });
      qc.invalidateQueries({ queryKey: ['unassigned', date] });
      onClose();
    },
  });

  const dialogRef = React.useRef<HTMLDivElement>(null);
  React.useEffect(() => {
    const el = dialogRef.current;
    const prev = document.activeElement as HTMLElement | null;
    el?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        e.preventDefault();
        onClose();
      }
      if (e.key === 'Tab' && el) {
        const focusable = Array.from(
          el.querySelectorAll<HTMLElement>(
            'a,button,input,select,textarea,[tabindex]:not([tabindex="-1"])'
          )
        );
        if (focusable.length === 0) return;
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (e.shiftKey) {
          if (document.activeElement === first) {
            e.preventDefault();
            last.focus();
          }
        } else {
          if (document.activeElement === last) {
            e.preventDefault();
            first.focus();
          }
        }
      }
    };
    el?.addEventListener('keydown', onKey);
    return () => {
      el?.removeEventListener('keydown', onKey);
      prev?.focus();
    };
  }, [onClose]);

  return (
    <div
      style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.3)' }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="assign-title"
        tabIndex={-1}
        style={{ background: '#fff', padding: 16, maxWidth: 320, margin: '10% auto' }}
      >
        <h3 id="assign-title">Assign to route</h3>
        {isLoading && <div role="status">Loading...</div>}
        {isError && <div role="alert">Failed to load</div>}
        {!isLoading && !isError && (
          <label>
            <span className="sr-only">Route</span>
            <select value={routeId} onChange={(e) => setRouteId(e.target.value)}>
              <option value="">Select route</option>
              {routes?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <div style={{ marginTop: 16 }}>
          <button onClick={() => mutation.mutate()} disabled={!routeId}>
            Assign
          </button>{' '}
          <button onClick={onClose}>Cancel</button>
        </div>
      </div>
    </div>
  );
}

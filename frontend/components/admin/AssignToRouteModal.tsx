import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchRoutes, assignOrdersToRoute } from '@/lib/apiAdapter';

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
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center p-4 z-50">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="assign-title"
        tabIndex={-1}
        className="card max-w-md w-full"
      >
        <h3 id="assign-title" className="text-lg font-semibold text-gray-900 mb-4">
          Assign {orderIds.length} order{orderIds.length === 1 ? '' : 's'} to route
        </h3>
        {isLoading && (
          <div className="flex items-center justify-center py-4" role="status">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
            Loading routes...
          </div>
        )}
        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded mb-4" role="alert">
            Failed to load routes
          </div>
        )}
        {!isLoading && !isError && (
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Select Route <span className="text-red-500">*</span>
            </label>
            <select 
              value={routeId} 
              onChange={(e) => setRouteId(e.target.value)}
              className="select w-full"
              required
            >
              <option value="">Choose a route...</option>
              {routes?.map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name}
                </option>
              ))}
            </select>
          </div>
        )}
        <div className="flex justify-end space-x-3 pt-4 mt-6 border-t border-gray-200">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button 
            onClick={() => mutation.mutate()} 
            disabled={!routeId || mutation.isPending}
            className="btn btn-primary"
          >
            {mutation.isPending ? (
              <span className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Assigning...
              </span>
            ) : (
              `Assign ${orderIds.length} Order${orderIds.length === 1 ? '' : 's'}`
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDrivers, createRoute, updateRoute } from '@/lib/apiAdapter';

interface Props {
  date: string;
  route?: { id: string; driverId?: string | null; secondaryDriverId?: string | null; name: string };
  onClose: () => void;
}

export default function RouteFormModal({ date, route, onClose }: Props) {
  const { data: drivers, isLoading, isError } = useQuery({
    queryKey: ['drivers'],
    queryFn: fetchDrivers,
  });
  const [driverId, setDriverId] = React.useState(route?.driverId || '');
  const [secondaryDriverId, setSecondaryDriverId] = React.useState(route?.secondaryDriverId || '');
  const [name, setName] = React.useState(route?.name || '');
  const qc = useQueryClient();
  const mutation = useMutation({
    mutationFn: () => {
      const routeData = {
        driver_id: driverId ? Number(driverId) : undefined,
        secondary_driver_id: secondaryDriverId ? Number(secondaryDriverId) : undefined,
        name: name || undefined,
      };
      return route
        ? updateRoute(route.id, routeData)
        : createRoute({
            driver_id: Number(driverId), // Required for create
            secondary_driver_id: secondaryDriverId ? Number(secondaryDriverId) : undefined,
            route_date: date,
            name: name || undefined,
          });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['routes', date] });
      onClose();
    },
  });
  return (
    <div className="fixed inset-0 bg-black bg-opacity-30 flex items-center justify-center p-4 z-50">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="route-form-title"
        tabIndex={-1}
        className="card max-w-md w-full"
      >
        <h3 id="route-form-title" className="text-lg font-semibold text-gray-900 mb-4">
          {route ? 'Edit route' : 'Create route'}
        </h3>
        {isLoading && (
          <div className="flex items-center justify-center py-4" role="status">
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-primary mr-2"></div>
            Loading drivers...
          </div>
        )}
        {isError && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-3 py-2 rounded mb-4" role="alert">
            Failed to load drivers
          </div>
        )}
        {!isLoading && !isError && (
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Primary Driver <span className="text-red-500">*</span>
              </label>
              <select 
                value={driverId} 
                onChange={(e) => setDriverId(e.target.value)}
                className="select"
                required
              >
                <option value="">Select primary driver</option>
                {drivers?.map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name || d.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Secondary Driver <span className="text-gray-400 text-xs">(optional)</span>
              </label>
              <select 
                value={secondaryDriverId} 
                onChange={(e) => setSecondaryDriverId(e.target.value)}
                className="select"
              >
                <option value="">No secondary driver</option>
                {drivers?.filter(d => d.id !== Number(driverId)).map((d) => (
                  <option key={d.id} value={d.id}>
                    {d.name || d.id}
                  </option>
                ))}
              </select>
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">
                Route Name
              </label>
              <input 
                value={name} 
                onChange={(e) => setName(e.target.value)}
                className="input"
                placeholder="Enter route name (optional)"
              />
            </div>
          </div>
        )}
        <div className="flex justify-end space-x-3 pt-4 mt-6 border-t border-gray-200">
          <button onClick={onClose} className="btn btn-secondary">
            Cancel
          </button>
          <button 
            onClick={() => mutation.mutate()} 
            disabled={!driverId || mutation.isPending}
            className="btn btn-primary"
          >
            {mutation.isPending ? (
              <span className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                {route ? 'Saving...' : 'Creating...'}
              </span>
            ) : (
              route ? 'Save Changes' : 'Create Route'
            )}
          </button>
        </div>
      </div>
    </div>
  );
}


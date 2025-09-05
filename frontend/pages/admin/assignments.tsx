import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import AdminLayout from '@/components/Layout/AdminLayout';
import { 
  Zap,
  CheckCircle, 
  AlertTriangle,
  Package,
  Users,
  RefreshCw,
  Sparkles
} from 'lucide-react';

interface Assignment {
  order_id: number;
  driver_id: number;
  driver_name: string;
  route_id: number;
  order_code: string;
}

interface AutoAssignResponse {
  success: boolean;
  message: string;
  total: number;
  assigned: Assignment[];
}

interface StatusResponse {
  orders_to_assign: number;
  available_drivers: number;
  orders: any[];
  drivers: any[];
}

export default function Assignments() {
  const queryClient = useQueryClient();
  const [lastResult, setLastResult] = useState<AutoAssignResponse | null>(null);

  // Get current status
  const { data: status, isLoading: statusLoading } = useQuery({
    queryKey: ['assignment-status'],
    queryFn: async () => {
      const response = await fetch('/api/assignment/status');
      if (!response.ok) throw new Error('Failed to get status');
      const result = await response.json();
      return result.data as StatusResponse;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Auto-assign mutation
  const autoAssignMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/api/assignment/auto-assign', {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Assignment failed');
      const result = await response.json();
      return result.data as AutoAssignResponse;
    },
    onSuccess: (data) => {
      setLastResult(data);
      queryClient.invalidateQueries({ queryKey: ['assignment-status'] });
    },
  });

  const handleAutoAssign = () => {
    autoAssignMutation.mutate();
  };

  return (
    <AdminLayout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">Order Assignment</h1>
            <p className="mt-1 text-sm text-gray-500">
              Automatically assign orders to scheduled drivers
            </p>
          </div>
        </div>

        {/* Status Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Orders to Assign */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Package className="h-8 w-8 text-blue-600" />
              </div>
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {statusLoading ? '...' : status?.orders_to_assign || 0}
                </div>
                <div className="text-sm text-gray-500">Orders Ready for Assignment</div>
              </div>
            </div>
          </div>

          {/* Available Drivers */}
          <div className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <Users className="h-8 w-8 text-green-600" />
              </div>
              <div className="ml-4">
                <div className="text-2xl font-bold text-gray-900">
                  {statusLoading ? '...' : status?.available_drivers || 0}
                </div>
                <div className="text-sm text-gray-500">Scheduled Drivers Available</div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Assignment Button */}
        <div className="bg-white rounded-lg shadow p-8 text-center">
          <div className="mx-auto flex items-center justify-center h-16 w-16 rounded-full bg-blue-100 mb-4">
            <Zap className="h-8 w-8 text-blue-600" />
          </div>
          <h3 className="text-lg font-medium text-gray-900 mb-2">
            Auto-Assign Orders
          </h3>
          <p className="text-sm text-gray-500 mb-6">
            Automatically assign all eligible orders to scheduled drivers using AI optimization
          </p>
          
          <button
            onClick={handleAutoAssign}
            disabled={autoAssignMutation.isPending || !status?.orders_to_assign || !status?.available_drivers}
            className="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {autoAssignMutation.isPending ? (
              <>
                <RefreshCw className="animate-spin -ml-1 mr-3 h-5 w-5" />
                Assigning...
              </>
            ) : (
              <>
                <Sparkles className="-ml-1 mr-3 h-5 w-5" />
                Assign All Orders
              </>
            )}
          </button>

          {(!status?.orders_to_assign || !status?.available_drivers) && (
            <p className="mt-3 text-sm text-gray-400">
              {!status?.orders_to_assign ? 'No orders to assign' : 'No scheduled drivers available'}
            </p>
          )}
        </div>

        {/* Last Assignment Result */}
        {lastResult && (
          <div className={`rounded-lg shadow p-6 ${lastResult.success ? 'bg-green-50 border border-green-200' : 'bg-red-50 border border-red-200'}`}>
            <div className="flex items-center">
              <div className="flex-shrink-0">
                {lastResult.success ? (
                  <CheckCircle className="h-6 w-6 text-green-600" />
                ) : (
                  <AlertTriangle className="h-6 w-6 text-red-600" />
                )}
              </div>
              <div className="ml-3">
                <h3 className={`text-sm font-medium ${lastResult.success ? 'text-green-800' : 'text-red-800'}`}>
                  Assignment Result
                </h3>
                <div className={`mt-1 text-sm ${lastResult.success ? 'text-green-700' : 'text-red-700'}`}>
                  {lastResult.message}
                </div>
                {lastResult.success && lastResult.assigned && lastResult.assigned.length > 0 && (
                  <div className="mt-3">
                    <h4 className="text-sm font-medium text-green-800">Assigned Orders:</h4>
                    <div className="mt-1 text-sm text-green-700">
                      {lastResult.assigned.map((assignment, index) => (
                        <div key={index} className="flex items-center justify-between py-1">
                          <span>Order {assignment.order_code}</span>
                          <span>→ {assignment.driver_name}</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Assignment Error */}
        {autoAssignMutation.isError && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="flex">
              <div className="flex-shrink-0">
                <AlertTriangle className="h-5 w-5 text-red-400" />
              </div>
              <div className="ml-3">
                <h3 className="text-sm font-medium text-red-800">
                  Assignment Failed
                </h3>
                <div className="mt-2 text-sm text-red-700">
                  {autoAssignMutation.error?.message || 'An unknown error occurred'}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Simple Status Display */}
        {status && (
          <div className="bg-white rounded-lg shadow p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">Current Status</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">Orders waiting for assignment</span>
                <span className="font-medium">{status.orders_to_assign}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-sm text-gray-500">Scheduled drivers available</span>
                <span className="font-medium">{status.available_drivers}</span>
              </div>
            </div>
          </div>
        )}
      </div>
    </AdminLayout>
  );
}
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import AdminLayout from '@/components/admin/AdminLayout';
import { 
  Sparkles as SparklesIcon, 
  CheckCircle as CheckCircleIcon, 
  AlertTriangle as ExclamationTriangleIcon,
  Truck as TruckIcon,
  Clock as ClockIcon,
  MapPin as MapPinIcon,
  ChevronRight as ChevronRightIcon
} from 'lucide-react';

interface Assignment {
  order_id: number;
  driver_id: number;
  driver_name: string;
  route_id: number;
  order_code: string;
}

interface Route {
  id: number;
  driver_id: number;
  driver_name: string;
  route_date: string;
  name: string;
}

interface AutoAssignResponse {
  success: boolean;
  message: string;
  assigned_count: number;
  routes_created: number;
  assignments: Assignment[];
  routes: Route[];
  failed: any[];
  method: string;
}

interface OnHoldOrder {
  order_id: number;
  order_code: string;
  customer_name: string;
  customer_phone?: string;
  address?: string;
  total: number;
  created_at?: string;
  on_hold_reason: string;
}

interface ManualEditSummary {
  date: string;
  routes_count: number;
  total_orders: number;
  routes: Array<{
    route_id: number;
    driver_id: number;
    driver_name: string;
    route_name: string;
    orders_count: number;
    orders: any[];
    can_add_secondary_driver: boolean;
  }>;
}

export default function UnifiedAssignmentsPage() {
  const [isAssigning, setIsAssigning] = useState(false);
  const [lastResult, setLastResult] = useState<AutoAssignResponse | null>(null);
  const queryClient = useQueryClient();

  // Fetch on-hold orders
  const { data: onHoldData } = useQuery({
    queryKey: ['unified-assignments', 'on-hold'],
    queryFn: async () => {
      const response = await fetch('/_api/unified-assignments/on-hold-orders');
      if (!response.ok) throw new Error('Failed to fetch on-hold orders');
      return response.json();
    }
  });

  // Fetch manual edit summary
  const { data: editSummary } = useQuery({
    queryKey: ['unified-assignments', 'summary'],
    queryFn: async () => {
      const response = await fetch('/_api/unified-assignments/manual-edit-summary');
      if (!response.ok) throw new Error('Failed to fetch edit summary');
      return response.json();
    }
  });

  // Auto-assign mutation
  const autoAssignMutation = useMutation({
    mutationFn: async () => {
      const response = await fetch('/_api/unified-assignments/auto-assign', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' }
      });
      if (!response.ok) throw new Error('Auto-assignment failed');
      return response.json();
    },
    onSuccess: (data: AutoAssignResponse) => {
      setLastResult(data);
      queryClient.invalidateQueries({ queryKey: ['unified-assignments'] });
    }
  });

  const handleAutoAssign = async () => {
    setIsAssigning(true);
    try {
      await autoAssignMutation.mutateAsync();
    } finally {
      setIsAssigning(false);
    }
  };

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center gap-3 mb-4">
          <div className="p-2 bg-gradient-to-br from-blue-500 to-purple-600 rounded-lg">
            <SparklesIcon className="h-6 w-6 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
            Unified Assignment Workflow
          </h1>
        </div>
        <p className="text-gray-600 dark:text-gray-300">
          Automate order assignment with smart suggestions and route creation. Manual editing available when needed.
        </p>
      </div>

      {/* Main Auto-Assign Section */}
      <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700 mb-8">
        <div className="p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
                Auto-Assignment Engine
              </h2>
              <p className="text-gray-600 dark:text-gray-300">
                Automatically assign all new orders using AI optimization and create delivery routes
              </p>
            </div>
            <button
              onClick={handleAutoAssign}
              disabled={isAssigning}
              className="px-6 py-3 bg-gradient-to-r from-blue-500 to-purple-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-purple-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 flex items-center gap-2"
            >
              {isAssigning ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent" />
                  Assigning...
                </>
              ) : (
                <>
                  <SparklesIcon className="h-5 w-5" />
                  Auto-Assign All Orders
                </>
              )}
            </button>
          </div>

          {/* Last Result */}
          {lastResult && (
            <div className={`p-4 rounded-lg border ${lastResult.success 
              ? 'bg-green-50 dark:bg-green-900/20 border-green-200 dark:border-green-800' 
              : 'bg-red-50 dark:bg-red-900/20 border-red-200 dark:border-red-800'
            }`}>
              <div className="flex items-center gap-2 mb-2">
                {lastResult.success ? (
                  <CheckCircleIcon className="h-5 w-5 text-green-600 dark:text-green-400" />
                ) : (
                  <ExclamationTriangleIcon className="h-5 w-5 text-red-600 dark:text-red-400" />
                )}
                <span className={`font-medium ${lastResult.success 
                  ? 'text-green-800 dark:text-green-200' 
                  : 'text-red-800 dark:text-red-200'
                }`}>
                  {lastResult.message}
                </span>
              </div>
              
              {lastResult.success && (
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                      {lastResult.assigned_count}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300">Orders Assigned</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                      {lastResult.routes_created}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300">Routes Created</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                      {lastResult.routes.length}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300">Active Routes</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-gray-600 dark:text-gray-300">
                      {lastResult.method === 'openai_optimized' ? 'AI' : 'Distance'}
                    </div>
                    <div className="text-sm text-gray-600 dark:text-gray-300">Method Used</div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {/* Dashboard Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* On-Hold Orders */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <ClockIcon className="h-5 w-5 text-amber-500" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                On-Hold Orders
              </h3>
              <span className="px-2 py-1 bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200 text-xs rounded-full">
                {onHoldData?.count || 0}
              </span>
            </div>
            
            {onHoldData?.on_hold_orders?.length > 0 ? (
              <div className="space-y-3">
                {onHoldData.on_hold_orders.slice(0, 5).map((order: OnHoldOrder) => (
                  <div key={order.order_id} className="flex items-center justify-between p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        #{order.order_code}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {order.customer_name}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-gray-900 dark:text-white">
                        RM{order.total}
                      </div>
                      <div className="text-xs text-amber-600 dark:text-amber-400">
                        Needs date input
                      </div>
                    </div>
                  </div>
                ))}
                {onHoldData.on_hold_orders.length > 5 && (
                  <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                    +{onHoldData.on_hold_orders.length - 5} more orders
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                No orders on hold
              </div>
            )}
          </div>
        </div>

        {/* Current Routes Summary */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow-lg border border-gray-200 dark:border-gray-700">
          <div className="p-6">
            <div className="flex items-center gap-2 mb-4">
              <TruckIcon className="h-5 w-5 text-blue-500" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                Today&apos;s Routes
              </h3>
              <span className="px-2 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 text-xs rounded-full">
                {editSummary?.routes_count || 0}
              </span>
            </div>
            
            {editSummary?.routes?.length > 0 ? (
              <div className="space-y-3">
                {editSummary.routes.slice(0, 5).map((route: any) => (
                  <div key={route.route_id} className="flex items-center justify-between p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                    <div>
                      <div className="font-medium text-gray-900 dark:text-white">
                        {route.driver_name}
                      </div>
                      <div className="text-sm text-gray-600 dark:text-gray-300">
                        {route.route_name}
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="font-medium text-gray-900 dark:text-white">
                        {route.orders_count} orders
                      </div>
                      <div className="text-xs text-blue-600 dark:text-blue-400">
                        {route.can_add_secondary_driver ? 'Can add helper' : 'Full capacity'}
                      </div>
                    </div>
                  </div>
                ))}
                {editSummary.routes.length > 5 && (
                  <div className="text-center text-sm text-gray-500 dark:text-gray-400">
                    +{editSummary.routes.length - 5} more routes
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-8 text-gray-500 dark:text-gray-400">
                No routes created yet
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="mt-8 bg-gradient-to-br from-gray-50 to-gray-100 dark:from-gray-800 dark:to-gray-700 rounded-xl p-6 border border-gray-200 dark:border-gray-600">
        <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-4">
          Manual Actions (When Needed)
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link
            href="/admin/routes"
            className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-600"
          >
            <MapPinIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Edit Routes</div>
              <div className="text-sm text-gray-600 dark:text-gray-300">Modify existing routes</div>
            </div>
            <ChevronRightIcon className="h-4 w-4 text-gray-400 ml-auto" />
          </Link>
          
          <Link
            href="/admin/assign"
            className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-600"
          >
            <TruckIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Manual Assign</div>
              <div className="text-sm text-gray-600 dark:text-gray-300">Assign specific orders</div>
            </div>
            <ChevronRightIcon className="h-4 w-4 text-gray-400 ml-auto" />
          </Link>
          
          <Link
            href="/admin/driver-schedule"
            className="flex items-center gap-3 p-4 bg-white dark:bg-gray-800 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors border border-gray-200 dark:border-gray-600"
          >
            <ClockIcon className="h-5 w-5 text-gray-600 dark:text-gray-300" />
            <div>
              <div className="font-medium text-gray-900 dark:text-white">Schedule Drivers</div>
              <div className="text-sm text-gray-600 dark:text-gray-300">Set availability patterns</div>
            </div>
            <ChevronRightIcon className="h-4 w-4 text-gray-400 ml-auto" />
          </Link>
        </div>
      </div>
    </div>
  );
}

(UnifiedAssignmentsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
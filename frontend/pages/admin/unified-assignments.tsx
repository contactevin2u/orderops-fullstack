import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Link from 'next/link';
import AdminLayout from '@/components/admin/AdminLayout';
import { 
  Sparkles, 
  CheckCircle, 
  AlertTriangle,
  Truck,
  Clock,
  MapPin,
  ChevronRight,
  Zap,
  BarChart3,
  RefreshCw,
  Activity,
  TrendingUp,
  Users,
  Package,
  Settings,
  Calendar
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
  const { data: onHoldData, isLoading: onHoldLoading } = useQuery({
    queryKey: ['unified-assignments', 'on-hold'],
    queryFn: async () => {
      const response = await fetch('/_api/unified-assignments/on-hold-orders');
      if (!response.ok) throw new Error('Failed to fetch on-hold orders');
      return response.json();
    }
  });

  // Fetch manual edit summary
  const { data: editSummary, isLoading: summaryLoading } = useQuery({
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

  const refreshData = () => {
    queryClient.invalidateQueries({ queryKey: ['unified-assignments'] });
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <div className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <div className="flex items-center justify-center h-12 w-12 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600">
                <Sparkles className="h-6 w-6 text-white" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  Auto Assignment Center
                </h1>
                <p className="mt-1 text-gray-600 dark:text-gray-300">
                  AI-powered order assignment and route optimization
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <button
                onClick={refreshData}
                className="inline-flex items-center px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-200 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors"
              >
                <RefreshCw className="h-4 w-4 mr-2" />
                Refresh
              </button>
              <button
                onClick={handleAutoAssign}
                disabled={isAssigning}
                className="inline-flex items-center px-6 py-3 bg-gradient-to-r from-purple-500 to-indigo-600 text-white font-semibold rounded-lg hover:from-purple-600 hover:to-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl"
              >
                {isAssigning ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Processing...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 mr-2" />
                    Auto-Assign Orders
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Success/Error Result */}
        {lastResult && (
          <div className={`mb-8 rounded-xl border p-6 ${
            lastResult.success 
              ? 'bg-green-50 dark:bg-green-900/10 border-green-200 dark:border-green-800' 
              : 'bg-red-50 dark:bg-red-900/10 border-red-200 dark:border-red-800'
          }`}>
            <div className="flex items-start space-x-3">
              {lastResult.success ? (
                <CheckCircle className="h-5 w-5 text-green-600 dark:text-green-400 mt-0.5" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
              )}
              <div className="flex-1">
                <h3 className={`text-sm font-medium ${
                  lastResult.success 
                    ? 'text-green-800 dark:text-green-200' 
                    : 'text-red-800 dark:text-red-200'
                }`}>
                  {lastResult.message}
                </h3>
                
                {lastResult.success && (
                  <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                        {lastResult.assigned_count}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                        Orders Assigned
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                        {lastResult.routes_created}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                        Routes Created
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                        {lastResult.routes.length}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                        Active Routes
                      </div>
                    </div>
                    <div className="bg-white dark:bg-gray-800 rounded-lg p-3 text-center">
                      <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                        {lastResult.method === 'openai_optimized' ? 'AI' : 'Distance'}
                      </div>
                      <div className="text-xs text-gray-600 dark:text-gray-300 uppercase tracking-wide">
                        Method Used
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Stats Overview */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-amber-100 dark:bg-amber-900/30">
                  <Clock className="h-5 w-5 text-amber-600 dark:text-amber-400" />
                </div>
              </div>
              <div className="ml-4">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  On-Hold Orders
                </h3>
                <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                  {onHoldLoading ? '...' : onHoldData?.count || 0}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-blue-100 dark:bg-blue-900/30">
                  <Truck className="h-5 w-5 text-blue-600 dark:text-blue-400" />
                </div>
              </div>
              <div className="ml-4">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Active Routes
                </h3>
                <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                  {summaryLoading ? '...' : editSummary?.routes_count || 0}
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700 p-6">
            <div className="flex items-center">
              <div className="flex-shrink-0">
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-green-100 dark:bg-green-900/30">
                  <Package className="h-5 w-5 text-green-600 dark:text-green-400" />
                </div>
              </div>
              <div className="ml-4">
                <h3 className="text-sm font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wide">
                  Total Orders
                </h3>
                <div className="mt-1 text-2xl font-semibold text-gray-900 dark:text-white">
                  {summaryLoading ? '...' : editSummary?.total_orders || 0}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Main Content */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
          {/* On-Hold Orders */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Orders Requiring Attention
                </h3>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-100 dark:bg-amber-900/30 text-amber-800 dark:text-amber-200">
                  {onHoldData?.count || 0} pending
                </span>
              </div>
            </div>
            <div className="p-6">
              {onHoldData?.on_hold_orders?.length > 0 ? (
                <div className="space-y-4">
                  {onHoldData.on_hold_orders.slice(0, 5).map((order: OnHoldOrder) => (
                    <div key={order.order_id} className="flex items-center justify-between p-4 bg-amber-50 dark:bg-amber-900/10 rounded-lg border border-amber-200 dark:border-amber-800">
                      <div>
                        <div className="font-medium text-gray-900 dark:text-white">
                          Order #{order.order_code}
                        </div>
                        <div className="text-sm text-gray-600 dark:text-gray-300">
                          {order.customer_name}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900 dark:text-white">
                          RM{order.total}
                        </div>
                        <div className="text-xs text-amber-600 dark:text-amber-400">
                          Awaiting customer date
                        </div>
                      </div>
                    </div>
                  ))}
                  {onHoldData.on_hold_orders.length > 5 && (
                    <div className="text-center py-2">
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        +{onHoldData.on_hold_orders.length - 5} more orders
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Clock className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    No orders on hold
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* Active Routes */}
          <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700">
              <div className="flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  Today&apos;s Active Routes
                </h3>
                <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200">
                  {editSummary?.routes_count || 0} routes
                </span>
              </div>
            </div>
            <div className="p-6">
              {editSummary?.routes?.length > 0 ? (
                <div className="space-y-4">
                  {editSummary.routes.slice(0, 5).map((route: any) => (
                    <div key={route.route_id} className="flex items-center justify-between p-4 bg-blue-50 dark:bg-blue-900/10 rounded-lg border border-blue-200 dark:border-blue-800">
                      <div className="flex items-center space-x-3">
                        <div className="flex-shrink-0">
                          <div className="flex items-center justify-center h-8 w-8 rounded-full bg-blue-500 text-white text-sm font-medium">
                            {route.driver_name.charAt(0).toUpperCase()}
                          </div>
                        </div>
                        <div>
                          <div className="font-medium text-gray-900 dark:text-white">
                            {route.driver_name}
                          </div>
                          <div className="text-sm text-gray-600 dark:text-gray-300">
                            {route.route_name}
                          </div>
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="font-semibold text-gray-900 dark:text-white">
                          {route.orders_count} orders
                        </div>
                        <div className="text-xs text-blue-600 dark:text-blue-400">
                          {route.can_add_secondary_driver ? 'Available' : 'At capacity'}
                        </div>
                      </div>
                    </div>
                  ))}
                  {editSummary.routes.length > 5 && (
                    <div className="text-center py-2">
                      <span className="text-sm text-gray-500 dark:text-gray-400">
                        +{editSummary.routes.length - 5} more routes
                      </span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-center py-12">
                  <Truck className="h-12 w-12 text-gray-400 mx-auto mb-4" />
                  <p className="text-gray-500 dark:text-gray-400">
                    No active routes today
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Quick Actions */}
        <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700">
          <div className="p-6 border-b border-gray-200 dark:border-gray-700">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
              Manual Management
            </h3>
            <p className="mt-1 text-sm text-gray-600 dark:text-gray-300">
              Access manual tools when automatic assignment needs adjustment
            </p>
          </div>
          <div className="p-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Link
                href="/admin/routes"
                className="group flex items-center p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200"
              >
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-gray-100 dark:bg-gray-700 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30">
                  <MapPin className="h-5 w-5 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                </div>
                <div className="ml-4 flex-1">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Manage Routes
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Edit and optimize delivery routes
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500" />
              </Link>
              
              <Link
                href="/admin/assign"
                className="group flex items-center p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200"
              >
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-gray-100 dark:bg-gray-700 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30">
                  <Users className="h-5 w-5 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                </div>
                <div className="ml-4 flex-1">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Manual Assignment
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Assign specific orders to drivers
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500" />
              </Link>
              
              <Link
                href="/admin/driver-schedule"
                className="group flex items-center p-4 rounded-lg border border-gray-200 dark:border-gray-600 hover:border-blue-500 dark:hover:border-blue-400 hover:bg-blue-50 dark:hover:bg-blue-900/10 transition-all duration-200"
              >
                <div className="flex items-center justify-center h-10 w-10 rounded-lg bg-gray-100 dark:bg-gray-700 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/30">
                  <Calendar className="h-5 w-5 text-gray-600 dark:text-gray-300 group-hover:text-blue-600 dark:group-hover:text-blue-400" />
                </div>
                <div className="ml-4 flex-1">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400">
                    Driver Scheduling
                  </h4>
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    Set driver availability patterns
                  </p>
                </div>
                <ChevronRight className="h-4 w-4 text-gray-400 group-hover:text-blue-500" />
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

(UnifiedAssignmentsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
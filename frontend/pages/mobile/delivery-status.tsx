import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { MapPin, Truck, Clock, CheckCircle, AlertCircle, Edit3, Save, X, Phone } from 'lucide-react';
import { fetchRoutes, fetchUnassigned, fetchDrivers, updateRoute, type Route, type Order, type Driver } from '@/utils/apiAdapter';

export default function MobileDeliveryStatusPage() {
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [editingOrder, setEditingOrder] = useState<string | null>(null);
  const [newRouteId, setNewRouteId] = useState<string>('');
  const router = useRouter();
  const qc = useQueryClient();

  // Fetch routes and orders for the selected date
  const routesQuery = useQuery({
    queryKey: ['mobile-routes', selectedDate],
    queryFn: () => fetchRoutes(selectedDate)
  });

  const unassignedQuery = useQuery({
    queryKey: ['mobile-unassigned', selectedDate], 
    queryFn: () => fetchUnassigned(selectedDate)
  });

  const driversQuery = useQuery({
    queryKey: ['mobile-drivers'],
    queryFn: fetchDrivers
  });

  // Update route assignment
  const updateRouteMutation = useMutation({
    mutationFn: async ({ routeId, driverId }: { routeId: string; driverId: string }) => {
      return updateRoute(routeId, { driver_id: parseInt(driverId) });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', selectedDate] });
      qc.invalidateQueries({ queryKey: ['mobile-unassigned', selectedDate] });
      setEditingOrder(null);
      setNewRouteId('');
    }
  });

  const routes = routesQuery.data || [];
  const unassignedOrders = unassignedQuery.data || [];
  const drivers = driversQuery.data || [];

  // Combine all orders from routes and unassigned
  const allOrders: Order[] = [
    ...unassignedOrders,
    ...routes.flatMap(route => 
      route.stops.map(stop => ({
        id: stop.orderId,
        orderNo: stop.orderId,
        status: 'ASSIGNED',
        deliveryDate: route.date,
        address: '',
        routeId: route.id,
        routeName: route.name,
        driverName: drivers.find(d => d.id === route.driverId)?.name
      }))
    )
  ];

  const getStatusIcon = (order: Order) => {
    if (order.trip?.status === 'DELIVERED') {
      return <CheckCircle className="w-5 h-5 text-green-600" />;
    } else if (order.trip?.status === 'STARTED') {
      return <Truck className="w-5 h-5 text-blue-600" />;
    } else if (order.routeId) {
      return <Clock className="w-5 h-5 text-yellow-600" />;
    } else {
      return <AlertCircle className="w-5 h-5 text-gray-600" />;
    }
  };

  const getStatusColor = (order: Order) => {
    if (order.trip?.status === 'DELIVERED') {
      return 'bg-green-100 text-green-800 border-green-200';
    } else if (order.trip?.status === 'STARTED') {
      return 'bg-blue-100 text-blue-800 border-blue-200';
    } else if (order.routeId) {
      return 'bg-yellow-100 text-yellow-800 border-yellow-200';
    } else {
      return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getStatusText = (order: Order) => {
    if (order.trip?.status) {
      return order.trip.status;
    } else if (order.routeId) {
      return 'ASSIGNED';
    } else {
      return 'UNASSIGNED';
    }
  };

  const handleSaveRoute = (orderId: string) => {
    if (newRouteId) {
      const route = routes.find(r => r.id === newRouteId);
      if (route && route.driverId) {
        updateRouteMutation.mutate({ 
          routeId: newRouteId, 
          driverId: route.driverId 
        });
      }
    }
  };

  const handleCancelEdit = () => {
    setEditingOrder(null);
    setNewRouteId('');
  };

  return (
    <>
      <Head>
        <title>Delivery Status - Mobile</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
        <link rel="manifest" href="/manifest.json" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="default" />
        <style>{`
          @media (min-width: 769px) {
            .mobile-only { display: none !important; }
            .desktop-message { display: flex !important; }
          }
          @media (max-width: 768px) {
            .mobile-only { display: block !important; }
            .desktop-message { display: none !important; }
            body { font-size: 14px; -webkit-user-select: none; user-select: none; }
            input, select, textarea { font-size: 16px !important; }
            button { min-height: 44px; min-width: 44px; }
            .touch-feedback:active { 
              background-color: rgba(0, 0, 0, 0.05); 
              transform: scale(0.98); 
            }
          }
        `}</style>
      </Head>

      {/* Desktop message */}
      <div className="desktop-message hidden min-h-screen bg-gray-50 flex items-center justify-center p-4">
        <div className="text-center max-w-md">
          <Truck className="w-16 h-16 text-blue-600 mx-auto mb-4" />
          <h1 className="text-2xl font-bold text-gray-900 mb-2">Mobile Only</h1>
          <p className="text-gray-600 mb-6">
            This delivery status page is optimized for mobile devices. Please access it from your phone or tablet.
          </p>
          <button
            onClick={() => router.push('/admin/routes')}
            className="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700 transition-colors"
          >
            Go to Desktop Routes
          </button>
        </div>
      </div>

      {/* Mobile interface */}
      <div className="mobile-only min-h-screen bg-gray-50">
        {/* Header */}
        <div className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-10">
          <div className="p-4">
            <div className="flex items-center justify-between mb-4">
              <h1 className="text-xl font-bold text-gray-900">Delivery Status</h1>
              <div className="flex items-center space-x-2 text-sm text-gray-600">
                <Truck className="w-4 h-4" />
                <span>{allOrders.length} orders</span>
              </div>
            </div>
            
            {/* Date selector */}
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => setSelectedDate(e.target.value)}
              className="w-full p-3 border border-gray-200 rounded-lg bg-white text-gray-900 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>

        {/* Content */}
        <div className="p-4 space-y-4">
          {(routesQuery.isLoading || unassignedQuery.isLoading) && (
            <div className="text-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto"></div>
              <p className="mt-2 text-gray-600">Loading orders...</p>
            </div>
          )}

          {(routesQuery.isError || unassignedQuery.isError) && (
            <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-center">
              <AlertCircle className="w-8 h-8 text-red-600 mx-auto mb-2" />
              <p className="text-red-800 font-medium">Failed to load data</p>
              <button
                onClick={() => {
                  routesQuery.refetch();
                  unassignedQuery.refetch();
                }}
                className="mt-2 text-red-600 hover:text-red-800 underline"
              >
                Try again
              </button>
            </div>
          )}

          {!routesQuery.isLoading && !unassignedQuery.isLoading && allOrders.length === 0 && (
            <div className="text-center py-12">
              <MapPin className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">No orders found</h3>
              <p className="text-gray-600">No orders for {selectedDate}</p>
            </div>
          )}

          {/* Order cards */}
          {allOrders.map((order: Order) => (
            <div key={order.id} className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
              {/* Order header */}
              <div className="p-4 border-b border-gray-100">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex items-center space-x-2">
                    {getStatusIcon(order)}
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getStatusColor(order)}`}>
                      {getStatusText(order)}
                    </span>
                  </div>
                  <div className="text-right">
                    <div className="text-sm font-medium text-gray-900">#{order.orderNo}</div>
                    <div className="text-xs text-gray-600">Order {order.id}</div>
                  </div>
                </div>

                <div className="text-sm text-gray-600 mb-2">
                  <div className="font-medium text-gray-900 truncate">{order.address || 'Address not available'}</div>
                  <div className="text-xs text-gray-500">{order.deliveryDate}</div>
                </div>
              </div>

              {/* Route assignment */}
              <div className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-sm text-gray-600">Route:</span>{' '}
                    {editingOrder === order.id ? (
                      <div className="mt-2">
                        <select
                          value={newRouteId}
                          onChange={(e) => setNewRouteId(e.target.value)}
                          className="w-full p-2 border border-gray-300 rounded-md text-sm focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                        >
                          <option value="">No Route</option>
                          {routes.map((route: Route) => (
                            <option key={route.id} value={route.id}>
                              {route.name} - {drivers.find(d => d.id === route.driverId)?.name || 'No driver'}
                            </option>
                          ))}
                        </select>
                        <div className="flex space-x-2 mt-2">
                          <button
                            onClick={() => handleSaveRoute(order.id)}
                            disabled={updateRouteMutation.isPending}
                            className="flex-1 bg-green-600 text-white px-3 py-2 rounded-md text-sm hover:bg-green-700 disabled:opacity-50 flex items-center justify-center space-x-1 touch-feedback"
                          >
                            <Save className="w-4 h-4" />
                            <span>Save</span>
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="flex-1 bg-gray-500 text-white px-3 py-2 rounded-md text-sm hover:bg-gray-600 flex items-center justify-center space-x-1 touch-feedback"
                          >
                            <X className="w-4 h-4" />
                            <span>Cancel</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <span className="font-medium text-gray-900">
                          {order.routeId ? 
                            (routes.find(r => r.id === order.routeId)?.name || 'Unknown route') : 
                            'Not assigned'
                          }
                        </span>
                        {order.routeId && (
                          <div className="text-xs text-gray-600 mt-1">
                            Driver: {drivers.find(d => d.id === routes.find(r => r.id === order.routeId)?.driverId)?.name || 'No driver'}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                  
                  {editingOrder !== order.id && (
                    <button
                      onClick={() => {
                        setEditingOrder(order.id);
                        setNewRouteId(order.routeId || '');
                      }}
                      className="p-2 text-blue-600 hover:bg-blue-50 rounded-md transition-colors touch-feedback"
                    >
                      <Edit3 className="w-4 h-4" />
                    </button>
                  )}
                </div>

                {/* Time stamps and additional info */}
                {order.trip && (
                  <div className="mt-3 pt-3 border-t border-gray-100 text-xs text-gray-600 space-y-1">
                    {order.trip.started_at && (
                      <div>Started: {new Date(order.trip.started_at).toLocaleString()}</div>
                    )}
                    {order.trip.delivered_at && (
                      <div>Delivered: {new Date(order.trip.delivered_at).toLocaleString()}</div>
                    )}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Route summary section */}
        {routes.length > 0 && (
          <div className="p-4">
            <h2 className="text-lg font-semibold text-gray-900 mb-3">Today&apos;s Routes</h2>
            <div className="space-y-2">
              {routes.map((route: Route) => (
                <div key={route.id} className="bg-white rounded-lg border border-gray-200 p-3">
                  <div className="flex items-center justify-between">
                    <div>
                      <div className="font-medium text-gray-900">{route.name}</div>
                      <div className="text-sm text-gray-600">
                        {drivers.find(d => d.id === route.driverId)?.name || 'No driver'} • {route.stops.length} stops
                      </div>
                    </div>
                    <div className="text-right">
                      <div className="text-sm font-medium text-blue-600">
                        {route.stops.length} orders
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Bottom padding for mobile scrolling */}
        <div className="h-20"></div>
      </div>
    </>
  );
}
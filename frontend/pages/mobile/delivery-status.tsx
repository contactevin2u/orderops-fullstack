import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { MapPin, Truck, Clock, CheckCircle, AlertCircle, Edit3, Save, X, Phone } from 'lucide-react';
import { fetchRoutes, fetchUnassigned, fetchOnHold, fetchDrivers, updateRoute, type Route, type Order, type Driver } from '@/utils/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';
import { listOrders } from '@/utils/api';

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

  const onHoldQuery = useQuery({
    queryKey: ['mobile-onhold', selectedDate],
    queryFn: () => fetchOnHold(selectedDate)
  });

  // Fetch all orders for the selected date to get full order details including addresses
  const allOrdersQuery = useQuery({
    queryKey: ['mobile-all-orders', selectedDate],
    queryFn: async () => {
      const { items } = await listOrders(undefined, undefined, undefined, 500, { date: selectedDate });
      return (items || []).map((item: any) => ({
        id: String(item.id ?? ''),
        orderNo: item.code || item.orderNo || String(item.id ?? ''),
        status: item.status || 'UNASSIGNED',
        deliveryDate: item.delivery_date || item.deliveryDate || '',
        address: item.address || [item.address1, item.address2].filter(Boolean).join(' ') || item.customer_address || '',
        routeId: item.route_id?.toString() ?? item.routeId?.toString() ?? (item.trip?.route_id != null ? String(item.trip.route_id) : null),
        trip: item.trip
      }));
    }
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
      qc.invalidateQueries({ queryKey: ['mobile-onhold', selectedDate] });
      setEditingOrder(null);
      setNewRouteId('');
    }
  });

  const routes = routesQuery.data || [];
  const unassignedOrders = unassignedQuery.data || [];
  const onHoldOrders = onHoldQuery.data || [];
  const allOrdersData = allOrdersQuery.data || [];
  const drivers = driversQuery.data || [];

  // Use the comprehensive order data with full addresses
  const allOrders = allOrdersData;

  const getStatusIcon = (order: Order) => {
    if (order.trip?.status === 'DELIVERED') {
      return <CheckCircle style={{ width: '20px', height: '20px', color: '#16a34a' }} />;
    } else if (order.trip?.status === 'STARTED') {
      return <Truck style={{ width: '20px', height: '20px', color: '#1d4ed8' }} />;
    } else if (order.routeId) {
      return <Clock style={{ width: '20px', height: '20px', color: '#ca8a04' }} />;
    } else {
      return <AlertCircle style={{ width: '20px', height: '20px', color: '#64748b' }} />;
    }
  };

  const getStatusColor = (order: Order) => {
    if (order.trip?.status === 'DELIVERED') {
      return 'status-delivered';
    } else if (order.trip?.status === 'STARTED') {
      return 'status-started';
    } else if (order.routeId) {
      return 'status-assigned';
    } else {
      return 'status-unassigned';
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
          body {
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background-color: #f8fafc;
            color: #1e293b;
          }
          
          .container {
            min-height: 100vh;
            background-color: #f8fafc;
          }
          
          .header {
            background-color: white;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            border-bottom: 1px solid #e2e8f0;
            position: sticky;
            top: 0;
            z-index: 10;
            padding: 16px;
          }
          
          .header-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
          }
          
          .header-title {
            font-size: 20px;
            font-weight: bold;
            color: #1e293b;
            margin: 0;
          }
          
          .header-stats {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 14px;
            color: #64748b;
          }
          
          .date-input {
            width: 100%;
            padding: 12px;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            background-color: white;
            color: #1e293b;
            font-size: 16px;
            box-sizing: border-box;
          }
          
          .date-input:focus {
            outline: none;
            border-color: #3b82f6;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
          }
          
          .content {
            padding: 16px;
          }
          
          .order-card {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
            margin-bottom: 16px;
            overflow: hidden;
          }
          
          .order-header {
            padding: 16px;
            border-bottom: 1px solid #f1f5f9;
          }
          
          .order-status-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 8px;
          }
          
          .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 4px 8px;
            border-radius: 16px;
            font-size: 12px;
            font-weight: 500;
            border: 1px solid;
          }
          
          .status-delivered {
            background-color: #f0fdf4;
            color: #15803d;
            border-color: #dcfce7;
          }
          
          .status-started {
            background-color: #eff6ff;
            color: #1d4ed8;
            border-color: #dbeafe;
          }
          
          .status-assigned {
            background-color: #fefce8;
            color: #ca8a04;
            border-color: #fef3c7;
          }
          
          .status-unassigned {
            background-color: #f8fafc;
            color: #64748b;
            border-color: #e2e8f0;
          }
          
          .order-info {
            text-align: right;
          }
          
          .order-number {
            font-size: 14px;
            font-weight: 500;
            color: #1e293b;
            margin: 0;
          }
          
          .order-id {
            font-size: 12px;
            color: #64748b;
            margin: 0;
          }
          
          .address-info {
            font-size: 14px;
            color: #64748b;
            margin: 8px 0;
          }
          
          .address-text {
            font-weight: 500;
            color: #1e293b;
            display: block;
            margin-bottom: 4px;
            overflow: hidden;
            text-overflow: ellipsis;
            white-space: nowrap;
          }
          
          .date-text {
            font-size: 12px;
            color: #9ca3af;
          }
          
          .order-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 4px;
            margin-top: 8px;
          }
          
          .order-badge {
            display: inline-block;
            white-space: nowrap;
          }
          
          .route-section {
            padding: 16px;
          }
          
          .route-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          
          .route-info {
            flex: 1;
          }
          
          .route-label {
            font-size: 14px;
            color: #64748b;
            margin-bottom: 4px;
          }
          
          .route-name {
            font-weight: 500;
            color: #1e293b;
          }
          
          .driver-info {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
          }
          
          .route-select {
            width: 100%;
            padding: 8px;
            border: 1px solid #d1d5db;
            border-radius: 6px;
            font-size: 14px;
            margin-top: 8px;
          }
          
          .route-actions {
            display: flex;
            gap: 8px;
            margin-top: 8px;
          }
          
          .btn {
            padding: 8px 12px;
            border: none;
            border-radius: 6px;
            font-size: 14px;
            font-weight: 500;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 4px;
            min-height: 44px;
            transition: all 0.2s;
          }
          
          .btn:active {
            transform: scale(0.98);
          }
          
          .btn-save {
            flex: 1;
            background-color: #16a34a;
            color: white;
          }
          
          .btn-save:hover {
            background-color: #15803d;
          }
          
          .btn-cancel {
            flex: 1;
            background-color: #6b7280;
            color: white;
          }
          
          .btn-cancel:hover {
            background-color: #4b5563;
          }
          
          .btn-edit {
            padding: 8px;
            color: #3b82f6;
            background-color: transparent;
            border-radius: 6px;
          }
          
          .btn-edit:hover {
            background-color: #eff6ff;
          }
          
          .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
          }
          
          .loading {
            text-align: center;
            padding: 48px 0;
          }
          
          .spinner {
            width: 32px;
            height: 32px;
            border: 2px solid #e2e8f0;
            border-top: 2px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 8px;
          }
          
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }
          
          .empty-state {
            text-align: center;
            padding: 48px 0;
          }
          
          .empty-icon {
            width: 48px;
            height: 48px;
            color: #9ca3af;
            margin: 0 auto 16px;
          }
          
          .error-state {
            background-color: #fef2f2;
            border: 1px solid #fecaca;
            border-radius: 8px;
            padding: 16px;
            text-align: center;
          }
          
          .error-icon {
            width: 32px;
            height: 32px;
            color: #dc2626;
            margin: 0 auto 8px;
          }
          
          .error-text {
            color: #991b1b;
            font-weight: 500;
            margin-bottom: 8px;
          }
          
          .error-retry {
            color: #dc2626;
            text-decoration: underline;
            background: none;
            border: none;
            cursor: pointer;
            font-size: 14px;
          }
          
          .trip-info {
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid #f1f5f9;
            font-size: 12px;
            color: #64748b;
          }
          
          .trip-info > div {
            margin-bottom: 4px;
          }
          
          .routes-summary {
            margin-top: 24px;
          }
          
          .section-title {
            font-size: 18px;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 12px;
          }
          
          .route-summary-card {
            background-color: white;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
            padding: 12px;
            margin-bottom: 8px;
          }
          
          .route-summary-content {
            display: flex;
            align-items: center;
            justify-content: space-between;
          }
          
          .route-summary-name {
            font-weight: 500;
            color: #1e293b;
            margin-bottom: 4px;
          }
          
          .route-summary-details {
            font-size: 14px;
            color: #64748b;
          }
          
          .route-summary-count {
            text-align: right;
          }
          
          .order-count {
            font-size: 14px;
            font-weight: 500;
            color: #3b82f6;
          }
          
          .bottom-spacer {
            height: 80px;
          }
          
          @media (min-width: 769px) {
            .mobile-only { display: none !important; }
            .desktop-message { display: flex !important; }
          }
          
          @media (max-width: 768px) {
            .mobile-only { display: block !important; }
            .desktop-message { display: none !important; }
            body { font-size: 14px; -webkit-user-select: none; user-select: none; }
          }
        `}</style>
      </Head>

      {/* Desktop message */}
      <div className="desktop-message" style={{ display: 'none', minHeight: '100vh', backgroundColor: '#f8fafc', alignItems: 'center', justifyContent: 'center', padding: '16px' }}>
        <div style={{ textAlign: 'center', maxWidth: '28rem' }}>
          <Truck style={{ width: '64px', height: '64px', color: '#3b82f6', margin: '0 auto 16px' }} />
          <h1 style={{ fontSize: '24px', fontWeight: 'bold', color: '#1e293b', marginBottom: '8px' }}>Mobile Only</h1>
          <p style={{ color: '#64748b', marginBottom: '24px' }}>
            This delivery status page is optimized for mobile devices. Please access it from your phone or tablet.
          </p>
          <button
            onClick={() => router.push('/admin/routes')}
            style={{ backgroundColor: '#3b82f6', color: 'white', padding: '8px 24px', borderRadius: '8px', border: 'none', cursor: 'pointer' }}
          >
            Go to Desktop Routes
          </button>
        </div>
      </div>

      {/* Mobile interface */}
      <div className="mobile-only container">
        {/* Header */}
        <div className="header">
          <div className="header-content">
            <h1 className="header-title">Delivery Status</h1>
            <div className="header-stats">
              <span style={{ color: '#2563eb', fontWeight: '500' }}>{routes.length} Routes</span>
              <span>•</span>
              <span style={{ color: '#ea580c', fontWeight: '500' }}>{unassignedOrders.length} Unassigned</span>
              <span>•</span>
              <span style={{ color: '#9333ea', fontWeight: '500' }}>{onHoldOrders.length} On Hold</span>
            </div>
          </div>
          
          {/* Date selector */}
          <input
            type="date"
            value={selectedDate}
            onChange={(e) => setSelectedDate(e.target.value)}
            className="date-input"
          />
        </div>

        {/* Content */}
        <div className="content">
          {(routesQuery.isLoading || unassignedQuery.isLoading || onHoldQuery.isLoading || allOrdersQuery.isLoading) && (
            <div className="loading">
              <div className="spinner"></div>
              <p style={{ color: '#64748b' }}>Loading orders...</p>
            </div>
          )}

          {(routesQuery.isError || unassignedQuery.isError || onHoldQuery.isError || allOrdersQuery.isError) && (
            <div className="error-state">
              <AlertCircle className="error-icon" />
              <p className="error-text">Failed to load data</p>
              <button
                onClick={() => {
                  routesQuery.refetch();
                  unassignedQuery.refetch();
                  onHoldQuery.refetch();
                  allOrdersQuery.refetch();
                }}
                className="error-retry"
              >
                Try again
              </button>
            </div>
          )}

          {!routesQuery.isLoading && !unassignedQuery.isLoading && !onHoldQuery.isLoading && !allOrdersQuery.isLoading && allOrders.length === 0 && (
            <div className="empty-state">
              <MapPin className="empty-icon" />
              <h3 style={{ fontSize: '18px', fontWeight: '500', color: '#1e293b', marginBottom: '8px' }}>No orders found</h3>
              <p style={{ color: '#64748b' }}>No orders for {selectedDate}</p>
            </div>
          )}

          {/* Order cards */}
          {allOrders.map((order: Order) => (
            <div key={order.id} className="order-card">
              {/* Order header */}
              <div className="order-header">
                <div className="order-status-row">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    {getStatusIcon(order)}
                    <span className={`status-badge ${getStatusColor(order)}`}>
                      {getStatusText(order)}
                    </span>
                  </div>
                  <div className="order-info">
                    <div className="order-number">#{order.orderNo}</div>
                    <div className="order-id">Order {order.id}</div>
                  </div>
                </div>

                <div className="address-info">
                  <div className="address-text">{order.address || 'Address not available'}</div>
                  <div className="date-text">{order.deliveryDate}</div>
                </div>

                {/* Order badges */}
                <div className="order-badges">
                  {getOrderBadges(order, selectedDate).map((badge, index) => (
                    <span
                      key={index}
                      className="order-badge"
                      style={{
                        backgroundColor: badge.startsWith('Overdue') ? '#fef2f2' : '#f8fafc',
                        color: badge.startsWith('Overdue') ? '#dc2626' : 
                               badge === 'No date' ? '#ea580c' : '#64748b',
                        border: `1px solid ${badge.startsWith('Overdue') ? '#fecaca' : 
                                             badge === 'No date' ? '#fed7aa' : '#e2e8f0'}`,
                        fontSize: '11px',
                        padding: '2px 6px',
                        borderRadius: '12px',
                        fontWeight: '500'
                      }}
                    >
                      {badge}
                    </span>
                  ))}
                </div>
              </div>

              {/* Route assignment */}
              <div className="route-section">
                <div className="route-content">
                  <div className="route-info">
                    <div className="route-label">Route:</div>
                    {editingOrder === order.id ? (
                      <div>
                        <select
                          value={newRouteId}
                          onChange={(e) => setNewRouteId(e.target.value)}
                          className="route-select"
                        >
                          <option value="">No Route</option>
                          {routes.map((route: Route) => {
                            const primaryDriver = drivers.find(d => d.id === route.driverId)?.name || 'No driver';
                            const secondaryDriver = route.secondaryDriverId ? drivers.find(d => d.id === route.secondaryDriverId)?.name : null;
                            const driverText = secondaryDriver ? `${primaryDriver} + ${secondaryDriver}` : primaryDriver;
                            
                            return (
                              <option key={route.id} value={route.id}>
                                {route.name} - {driverText}
                              </option>
                            );
                          })}
                        </select>
                        <div className="route-actions">
                          <button
                            onClick={() => handleSaveRoute(order.id)}
                            disabled={updateRouteMutation.isPending}
                            className="btn btn-save"
                          >
                            <Save style={{ width: '16px', height: '16px' }} />
                            <span>Save</span>
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="btn btn-cancel"
                          >
                            <X style={{ width: '16px', height: '16px' }} />
                            <span>Cancel</span>
                          </button>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div className="route-name">
                          {order.routeId ? 
                            (routes.find(r => r.id === order.routeId)?.name || 'Unknown route') : 
                            'Not assigned'
                          }
                        </div>
                        {order.routeId && (
                          <div className="driver-info">
                            <div>
                              Primary: {drivers.find(d => d.id === routes.find(r => r.id === order.routeId)?.driverId)?.name || 'No driver'}
                            </div>
                            {routes.find(r => r.id === order.routeId)?.secondaryDriverId && (
                              <div>
                                Secondary: {drivers.find(d => d.id === routes.find(r => r.id === order.routeId)?.secondaryDriverId)?.name || 'No driver'}
                              </div>
                            )}
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
                      className="btn btn-edit"
                    >
                      <Edit3 style={{ width: '16px', height: '16px' }} />
                    </button>
                  )}
                </div>

                {/* Time stamps and additional info */}
                {order.trip && (
                  <div className="trip-info">
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
          <div className="routes-summary">
            <h2 className="section-title">Today&apos;s Routes</h2>
            <div>
              {routes.map((route: Route) => (
                <div key={route.id} className="route-summary-card">
                  <div className="route-summary-content">
                    <div>
                      <div className="route-summary-name">{route.name}</div>
                      <div className="route-summary-details">
                        {(() => {
                          const primaryDriver = drivers.find(d => d.id === route.driverId)?.name || 'No driver';
                          const secondaryDriver = route.secondaryDriverId ? drivers.find(d => d.id === route.secondaryDriverId)?.name : null;
                          const driverText = secondaryDriver ? `${primaryDriver} + ${secondaryDriver}` : primaryDriver;
                          return `${driverText} • ${route.stops.length} stops`;
                        })()}
                      </div>
                    </div>
                    <div className="route-summary-count">
                      <div className="order-count">
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
        <div className="bottom-spacer"></div>
      </div>
    </>
  );
}
import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { MapPin, Truck, CheckCircle, AlertCircle, ArrowLeft, Plus, X, Users } from 'lucide-react';
import { fetchRoutes, fetchUnassigned, fetchDrivers, updateRoute, addOrdersToRoute, type Route, type Order, type Driver } from '@/utils/apiAdapter';

export default function MobileDeliveryStatusPage() {
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [showUnassigned, setShowUnassigned] = useState(false);
  const [showDriverSelector, setShowDriverSelector] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();
  
  const today = new Date().toISOString().slice(0, 10);

  // Fetch today's data
  const routesQuery = useQuery({
    queryKey: ['mobile-routes', today],
    queryFn: () => fetchRoutes(today)
  });

  const unassignedQuery = useQuery({
    queryKey: ['mobile-unassigned', today],
    queryFn: () => fetchUnassigned(today)
  });

  const driversQuery = useQuery({
    queryKey: ['mobile-drivers'],
    queryFn: fetchDrivers
  });

  // Add orders to route mutation
  const addOrdersMutation = useMutation({
    mutationFn: async ({ routeId, orderIds }: { routeId: string; orderIds: number[] }) => {
      return addOrdersToRoute(parseInt(routeId), orderIds);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', today] });
      qc.invalidateQueries({ queryKey: ['mobile-unassigned', today] });
    }
  });

  // Update route mutation (for secondary driver)
  const updateRouteMutation = useMutation({
    mutationFn: async ({ routeId, updates }: { routeId: string; updates: any }) => {
      return updateRoute(routeId, updates);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', today] });
      setShowDriverSelector(false);
    }
  });

  const routes = routesQuery.data || [];
  const unassignedOrders = unassignedQuery.data || [];
  const drivers = driversQuery.data || [];

  // Calculate route statistics
  const getRouteStats = (route: Route) => {
    const totalTrips = route.stops?.length || 0;
    const deliveredTrips = route.stops?.filter(stop => stop.status === 'DELIVERED').length || 0;
    return { totalTrips, deliveredTrips };
  };

  // Add order to route
  const handleAddOrder = (orderId: number) => {
    if (selectedRoute) {
      addOrdersMutation.mutate({
        routeId: selectedRoute.id,
        orderIds: [orderId]
      });
    }
  };

  // Set secondary driver
  const handleSetSecondaryDriver = (driverId: string) => {
    if (selectedRoute) {
      updateRouteMutation.mutate({
        routeId: selectedRoute.id,
        updates: { secondary_driver_id: parseInt(driverId) }
      });
    }
  };

  if (routesQuery.isLoading || unassignedQuery.isLoading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: '100vh', background: '#f8fafc' }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{ width: '32px', height: '32px', border: '2px solid #e2e8f0', borderTop: '2px solid #3b82f6', borderRadius: '50%', animation: 'spin 1s linear infinite', margin: '0 auto 8px' }}></div>
          <p style={{ color: '#64748b' }}>Loading routes...</p>
        </div>
      </div>
    );
  }

  // Route detail view
  if (selectedRoute) {
    const { totalTrips, deliveredTrips } = getRouteStats(selectedRoute);
    const primaryDriver = drivers.find(d => d.id === selectedRoute.driverId);
    const secondaryDriver = drivers.find(d => d.id === selectedRoute.secondaryDriverId);

    return (
      <>
        <Head>
          <title>Route Details - {selectedRoute.name}</title>
          <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
          <style>{`
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; }
            .header { background: white; padding: 16px; border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 10; }
            .header-content { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
            .back-btn { background: none; border: none; color: #3b82f6; cursor: pointer; padding: 8px; border-radius: 8px; }
            .back-btn:hover { background: #eff6ff; }
            .route-title { font-size: 20px; font-weight: bold; color: #1e293b; }
            .route-stats { display: flex; gap: 16px; font-size: 14px; }
            .stat { text-align: center; }
            .stat-value { font-size: 18px; font-weight: bold; color: #1e293b; }
            .stat-label { color: #64748b; margin-top: 2px; }
            .drivers-section { background: white; margin: 16px; padding: 16px; border-radius: 12px; border: 1px solid #e2e8f0; }
            .driver-row { display: flex; align-items: center; justify-content: space-between; padding: 8px 0; }
            .driver-info { display: flex; align-items: center; gap: 8px; }
            .driver-label { font-size: 12px; color: #64748b; background: #f1f5f9; padding: 2px 6px; border-radius: 4px; }
            .driver-name { font-weight: 500; color: #1e293b; }
            .add-secondary-btn { background: #3b82f6; color: white; border: none; padding: 6px 12px; border-radius: 6px; font-size: 12px; cursor: pointer; }
            .orders-section { margin: 16px; }
            .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 12px; }
            .section-title { font-size: 16px; font-weight: 600; color: #1e293b; }
            .add-orders-btn { background: #16a34a; color: white; border: none; padding: 8px 12px; border-radius: 6px; font-size: 14px; cursor: pointer; display: flex; align-items: center; gap: 4px; }
            .order-card { background: white; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; margin-bottom: 8px; }
            .order-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
            .order-code { font-weight: 600; color: #1e293b; }
            .status-badge { font-size: 11px; padding: 3px 8px; border-radius: 12px; font-weight: 500; }
            .status-delivered { background: #f0fdf4; color: #15803d; border: 1px solid #dcfce7; }
            .status-started { background: #eff6ff; color: #1d4ed8; border: 1px solid #dbeafe; }
            .status-assigned { background: #fefce8; color: #ca8a04; border: 1px solid #fef3c7; }
            .order-address { font-size: 13px; color: #64748b; margin-top: 4px; }
            .modal { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.5); z-index: 50; display: flex; align-items: center; justify-content: center; }
            .modal-content { background: white; border-radius: 12px; width: 90%; max-width: 400px; max-height: 80%; overflow: auto; }
            .modal-header { padding: 16px; border-bottom: 1px solid #e2e8f0; display: flex; justify-content: between; align-items: center; }
            .modal-title { font-size: 18px; font-weight: 600; }
            .close-btn { background: none; border: none; color: #64748b; cursor: pointer; padding: 4px; }
            .modal-body { padding: 16px; }
            .driver-option { display: flex; align-items: center; padding: 12px; border: 1px solid #e2e8f0; border-radius: 8px; margin-bottom: 8px; cursor: pointer; }
            .driver-option:hover { background: #f8fafc; }
            .driver-option.selected { background: #eff6ff; border-color: #3b82f6; }
            .empty-state { text-align: center; padding: 32px 16px; color: #64748b; }
            @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
          `}</style>
        </Head>

        <div className="header">
          <div className="header-content">
            <button className="back-btn" onClick={() => setSelectedRoute(null)}>
              <ArrowLeft size={20} />
            </button>
            <h1 className="route-title">{selectedRoute.name}</h1>
          </div>
          <div className="route-stats">
            <div className="stat">
              <div className="stat-value">{totalTrips}</div>
              <div className="stat-label">Total Trips</div>
            </div>
            <div className="stat">
              <div className="stat-value">{deliveredTrips}</div>
              <div className="stat-label">Delivered</div>
            </div>
            <div className="stat">
              <div className="stat-value">{totalTrips - deliveredTrips}</div>
              <div className="stat-label">Pending</div>
            </div>
          </div>
        </div>

        <div className="drivers-section">
          <div className="driver-row">
            <div className="driver-info">
              <span className="driver-label">PRIMARY</span>
              <span className="driver-name">{primaryDriver?.name || 'Not assigned'}</span>
            </div>
          </div>
          <div className="driver-row">
            <div className="driver-info">
              <span className="driver-label">SECONDARY</span>
              <span className="driver-name">{secondaryDriver?.name || 'Not assigned'}</span>
            </div>
            <button 
              className="add-secondary-btn" 
              onClick={() => setShowDriverSelector(true)}
            >
              {secondaryDriver ? 'Change' : 'Add'}
            </button>
          </div>
        </div>

        <div className="orders-section">
          <div className="section-header">
            <h2 className="section-title">Assigned Orders ({totalTrips})</h2>
            <button 
              className="add-orders-btn" 
              onClick={() => setShowUnassigned(true)}
            >
              <Plus size={16} />
              Add Orders
            </button>
          </div>

          {selectedRoute.stops?.map((stop, index) => (
            <div key={stop.id || index} className="order-card">
              <div className="order-header">
                <span className="order-code">#{stop.orderNo || stop.id}</span>
                <span className={`status-badge status-${stop.status?.toLowerCase() || 'assigned'}`}>
                  {stop.status || 'ASSIGNED'}
                </span>
              </div>
              <div className="order-address">{stop.address || 'No address available'}</div>
            </div>
          )) || (
            <div className="empty-state">
              <p>No orders assigned to this route</p>
            </div>
          )}
        </div>

        {/* Driver selector modal */}
        {showDriverSelector && (
          <div className="modal">
            <div className="modal-content">
              <div className="modal-header">
                <h3 className="modal-title">Select Secondary Driver</h3>
                <button className="close-btn" onClick={() => setShowDriverSelector(false)}>
                  <X size={20} />
                </button>
              </div>
              <div className="modal-body">
                <div 
                  className="driver-option"
                  onClick={() => handleSetSecondaryDriver('')}
                >
                  <span>Remove Secondary Driver</span>
                </div>
                {drivers.filter(d => d.id !== selectedRoute.driverId).map(driver => (
                  <div 
                    key={driver.id}
                    className="driver-option"
                    onClick={() => handleSetSecondaryDriver(driver.id)}
                  >
                    <span>{driver.name}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Unassigned orders modal */}
        {showUnassigned && (
          <div className="modal">
            <div className="modal-content">
              <div className="modal-header">
                <h3 className="modal-title">Add Orders to Route</h3>
                <button className="close-btn" onClick={() => setShowUnassigned(false)}>
                  <X size={20} />
                </button>
              </div>
              <div className="modal-body">
                {unassignedOrders.length === 0 ? (
                  <div className="empty-state">
                    <p>No unassigned orders available</p>
                  </div>
                ) : (
                  unassignedOrders.map(order => (
                    <div 
                      key={order.id}
                      className="order-card"
                      onClick={() => handleAddOrder(parseInt(order.id))}
                      style={{ cursor: 'pointer' }}
                    >
                      <div className="order-header">
                        <span className="order-code">#{order.orderNo || order.id}</span>
                        <Plus size={16} color="#16a34a" />
                      </div>
                      <div className="order-address">{order.address || 'No address available'}</div>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        )}
      </>
    );
  }

  // Main routes view
  return (
    <>
      <Head>
        <title>Delivery Routes - Today</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1, user-scalable=no" />
        <style>{`
          * { box-sizing: border-box; margin: 0; padding: 0; }
          body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: #f8fafc; }
          .header { background: white; padding: 16px; border-bottom: 1px solid #e2e8f0; text-align: center; }
          .header-title { font-size: 24px; font-weight: bold; color: #1e293b; margin-bottom: 8px; }
          .header-date { color: #64748b; font-size: 14px; }
          .stats-row { display: flex; justify-content: space-around; padding: 16px; background: white; margin: 16px; border-radius: 12px; border: 1px solid #e2e8f0; }
          .stat { text-align: center; }
          .stat-value { font-size: 20px; font-weight: bold; color: #1e293b; }
          .stat-label { color: #64748b; font-size: 12px; margin-top: 4px; }
          .routes-section { margin: 16px; }
          .section-title { font-size: 18px; font-weight: 600; color: #1e293b; margin-bottom: 12px; }
          .route-card { background: white; border: 1px solid #e2e8f0; border-radius: 12px; padding: 16px; margin-bottom: 12px; cursor: pointer; transition: all 0.2s; }
          .route-card:hover { border-color: #3b82f6; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.15); }
          .route-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
          .route-name { font-size: 16px; font-weight: 600; color: #1e293b; }
          .route-stats { display: flex; gap: 12px; }
          .route-stat { font-size: 12px; color: #64748b; }
          .route-drivers { margin-top: 8px; }
          .driver-item { display: flex; align-items: center; gap: 6px; font-size: 13px; color: #64748b; margin-bottom: 4px; }
          .driver-role { background: #f1f5f9; padding: 1px 4px; border-radius: 3px; font-size: 10px; }
          .empty-state { text-align: center; padding: 48px 16px; }
          .empty-icon { width: 48px; height: 48px; color: #9ca3af; margin: 0 auto 16px; }
          @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
        `}</style>
      </Head>

      <div className="header">
        <h1 className="header-title">Today's Routes</h1>
        <div className="header-date">{new Date().toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}</div>
      </div>

      <div className="stats-row">
        <div className="stat">
          <div className="stat-value">{routes.length}</div>
          <div className="stat-label">Routes</div>
        </div>
        <div className="stat">
          <div className="stat-value">{routes.reduce((sum, route) => sum + (route.stops?.length || 0), 0)}</div>
          <div className="stat-label">Total Orders</div>
        </div>
        <div className="stat">
          <div className="stat-value">{routes.reduce((sum, route) => sum + (route.stops?.filter(s => s.status === 'DELIVERED').length || 0), 0)}</div>
          <div className="stat-label">Delivered</div>
        </div>
        <div className="stat">
          <div className="stat-value">{unassignedOrders.length}</div>
          <div className="stat-label">Unassigned</div>
        </div>
      </div>

      <div className="routes-section">
        <h2 className="section-title">Routes</h2>
        
        {routes.length === 0 ? (
          <div className="empty-state">
            <Truck className="empty-icon" />
            <h3 style={{ fontSize: '18px', fontWeight: '500', color: '#1e293b', marginBottom: '8px' }}>No routes today</h3>
            <p style={{ color: '#64748b' }}>Routes will appear here when created</p>
          </div>
        ) : (
          routes.map(route => {
            const { totalTrips, deliveredTrips } = getRouteStats(route);
            const primaryDriver = drivers.find(d => d.id === route.driverId);
            const secondaryDriver = drivers.find(d => d.id === route.secondaryDriverId);
            
            return (
              <div 
                key={route.id} 
                className="route-card"
                onClick={() => setSelectedRoute(route)}
              >
                <div className="route-header">
                  <span className="route-name">{route.name}</span>
                  <div className="route-stats">
                    <span className="route-stat">{totalTrips} orders</span>
                    <span className="route-stat">•</span>
                    <span className="route-stat">{deliveredTrips} delivered</span>
                  </div>
                </div>
                
                <div className="route-drivers">
                  {primaryDriver && (
                    <div className="driver-item">
                      <span className="driver-role">PRIMARY</span>
                      <span>{primaryDriver.name}</span>
                    </div>
                  )}
                  {secondaryDriver && (
                    <div className="driver-item">
                      <span className="driver-role">SECONDARY</span>
                      <span>{secondaryDriver.name}</span>
                    </div>
                  )}
                  {!primaryDriver && !secondaryDriver && (
                    <div className="driver-item">
                      <span style={{ color: '#ef4444' }}>No drivers assigned</span>
                    </div>
                  )}
                </div>
              </div>
            );
          })
        )}
      </div>
    </>
  );
}
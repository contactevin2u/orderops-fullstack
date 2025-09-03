import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useRouter } from 'next/router';
import Head from 'next/head';
import { MapPin, Truck, CheckCircle, AlertCircle, ArrowLeft, Plus, X, Users, Package } from 'lucide-react';
import { 
  fetchRoutes, 
  fetchUnassigned, 
  fetchDrivers, 
  updateRoute, 
  assignOrdersToRoute, 
  fetchRouteOrders,
  removeOrdersFromRoute,
  type Route, 
  type Order, 
  type Driver 
} from '@/utils/apiAdapter';
import { getOrderBadges } from '@/utils/orderBadges';

export default function MobileDeliveryStatusPage() {
  const [selectedRoute, setSelectedRoute] = useState<Route | null>(null);
  const [showUnassigned, setShowUnassigned] = useState(false);
  const [showDriverSelector, setShowDriverSelector] = useState(false);
  const [selectedOrders, setSelectedOrders] = useState<Set<string>>(new Set());
  const [showDesktopRedirect, setShowDesktopRedirect] = useState(false);
  const router = useRouter();
  const qc = useQueryClient();
  
  const today = new Date().toISOString().slice(0, 10);

  // Check if user is on desktop and show redirect prompt
  useEffect(() => {
    const checkDevice = () => {
      const isMobile = /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      const isSmallScreen = window.innerWidth < 768;
      
      if (!isMobile && !isSmallScreen) {
        setShowDesktopRedirect(true);
      }
    };

    checkDevice();
    window.addEventListener('resize', checkDevice);
    return () => window.removeEventListener('resize', checkDevice);
  }, []);

  const handleGoToAdmin = () => {
    router.push('/admin/routes');
  };

  // Fetch today's data
  const routesQuery = useQuery({
    queryKey: ['mobile-routes', today],
    queryFn: () => fetchRoutes(today),
    refetchInterval: 30000 // Refetch every 30 seconds
  });

  const unassignedQuery = useQuery({
    queryKey: ['mobile-unassigned', today],
    queryFn: () => fetchUnassigned(today),
    refetchInterval: 30000
  });

  const driversQuery = useQuery({
    queryKey: ['mobile-drivers'],
    queryFn: fetchDrivers
  });

  // Fetch orders for selected route
  const routeOrdersQuery = useQuery({
    queryKey: ['mobile-route-orders', selectedRoute?.id, today],
    queryFn: () => selectedRoute ? fetchRouteOrders(selectedRoute.id, today) : Promise.resolve([]),
    enabled: !!selectedRoute,
    refetchInterval: 30000
  });

  const routes = routesQuery.data || [];
  const unassignedOrders = unassignedQuery.data || [];
  const drivers = driversQuery.data || [];
  const routeOrders = routeOrdersQuery.data || [];

  const driverNameById = React.useMemo(() => {
    const map: Record<string, string> = {};
    drivers.forEach((d) => {
      map[d.id] = d.name || '';
    });
    return map;
  }, [drivers]);

  // Add orders to route mutation
  const addOrdersMutation = useMutation({
    mutationFn: async ({ routeId, orderIds }: { routeId: string; orderIds: string[] }) => {
      return assignOrdersToRoute(routeId, orderIds);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', today] });
      qc.invalidateQueries({ queryKey: ['mobile-unassigned', today] });
      qc.invalidateQueries({ queryKey: ['mobile-route-orders', selectedRoute?.id, today] });
      setSelectedOrders(new Set());
      setShowUnassigned(false);
    }
  });

  // Remove orders from route mutation
  const removeOrdersMutation = useMutation({
    mutationFn: async ({ routeId, orderIds }: { routeId: string; orderIds: string[] }) => {
      return removeOrdersFromRoute(routeId, orderIds);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', today] });
      qc.invalidateQueries({ queryKey: ['mobile-unassigned', today] });
      qc.invalidateQueries({ queryKey: ['mobile-route-orders', selectedRoute?.id, today] });
    }
  });

  // Update route mutation
  const updateRouteMutation = useMutation({
    mutationFn: async ({ routeId, updates }: { routeId: string; updates: any }) => {
      return updateRoute(routeId, updates);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['mobile-routes', today] });
      setShowDriverSelector(false);
    }
  });

  const handleAddOrders = () => {
    if (selectedRoute && selectedOrders.size > 0) {
      addOrdersMutation.mutate({
        routeId: selectedRoute.id,
        orderIds: Array.from(selectedOrders)
      });
    }
  };

  const handleRemoveOrder = (orderId: string) => {
    if (selectedRoute) {
      removeOrdersMutation.mutate({
        routeId: selectedRoute.id,
        orderIds: [orderId]
      });
    }
  };

  const handleAssignDriver = (driverId: string, isSecondary: boolean = false) => {
    if (selectedRoute) {
      const updates = isSecondary 
        ? { secondary_driver_id: parseInt(driverId) }
        : { driver_id: parseInt(driverId) };
      
      updateRouteMutation.mutate({
        routeId: selectedRoute.id,
        updates
      });
    }
  };

  const toggleOrderSelection = (orderId: string) => {
    const newSelected = new Set(selectedOrders);
    if (newSelected.has(orderId)) {
      newSelected.delete(orderId);
    } else {
      newSelected.add(orderId);
    }
    setSelectedOrders(newSelected);
  };

  const getOrderStatusColor = (status: string) => {
    switch (status) {
      case 'DELIVERED': return '#10b981';
      case 'STARTED': return '#f59e0b';
      case 'ON_HOLD': return '#8b5cf6';
      case 'CANCELLED': return '#ef4444';
      default: return '#6b7280';
    }
  };

  if (routesQuery.isLoading) {
    return (
      <div className="mobile-container">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>Loading routes...</p>
        </div>
        <style jsx>{`
          .mobile-container {
            min-height: 100vh;
            background: #f8fafc;
            padding: 1rem;
          }
          .loading-state {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            height: 50vh;
          }
          .loading-spinner {
            width: 2rem;
            height: 2rem;
            border: 3px solid #e2e8f0;
            border-top: 3px solid #3b82f6;
            border-radius: 50%;
            animation: spin 1s linear infinite;
          }
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}</style>
      </div>
    );
  }

  // Route detail view
  if (selectedRoute) {
    return (
      <>
        <Head>
          <title>Route Details - {selectedRoute.name}</title>
          <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
        </Head>

        <div className="mobile-container">
          {/* Header */}
          <div className="route-header">
            <button className="back-btn" onClick={() => setSelectedRoute(null)}>
              <ArrowLeft size={20} />
            </button>
            <div className="route-info">
              <h1 className="route-title">{selectedRoute.name}</h1>
              <div className="route-meta">
                <span className="driver-name">
                  {driverNameById[selectedRoute.driverId || ''] || 'No Driver'}
                </span>
                {selectedRoute.secondaryDriverId && (
                  <span className="secondary-driver">
                    + {driverNameById[selectedRoute.secondaryDriverId]}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Route Stats */}
          <div className="route-stats">
            <div className="stat-item">
              <Package size={16} />
              <span>{routeOrders.length} Orders</span>
            </div>
            <div className="stat-item">
              <CheckCircle size={16} />
              <span>{routeOrders.filter(o => o.status === 'DELIVERED').length} Delivered</span>
            </div>
            <div className="stat-item">
              <Truck size={16} />
              <span>{routeOrders.filter(o => o.status === 'STARTED').length} In Transit</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="action-buttons">
            <button 
              className="action-btn primary"
              onClick={() => setShowUnassigned(true)}
              disabled={addOrdersMutation.isPending}
            >
              <Plus size={18} />
              Add Orders
            </button>
            <button 
              className="action-btn secondary"
              onClick={() => setShowDriverSelector(true)}
            >
              <Users size={18} />
              Assign Driver
            </button>
          </div>

          {/* Route Orders */}
          <div className="orders-section">
            <h3 className="section-title">Assigned Orders ({routeOrders.length})</h3>
            
            {routeOrdersQuery.isLoading ? (
              <div className="loading-orders">Loading orders...</div>
            ) : routeOrders.length === 0 ? (
              <div className="empty-state">
                <Package size={48} />
                <p>No orders assigned to this route</p>
                <button className="add-first-btn" onClick={() => setShowUnassigned(true)}>
                  Add First Order
                </button>
              </div>
            ) : (
              <div className="orders-list">
                {routeOrders.map((order) => (
                  <div key={order.id} className="order-card">
                    <div className="order-header">
                      <div className="order-info">
                        <span className="order-code">#{order.orderNo}</span>
                        <span 
                          className="order-status"
                          style={{ color: getOrderStatusColor(order.status) }}
                        >
                          {order.status}
                        </span>
                      </div>
                      <button 
                        className="remove-btn"
                        onClick={() => handleRemoveOrder(order.id)}
                        disabled={removeOrdersMutation.isPending}
                      >
                        <X size={16} />
                      </button>
                    </div>
                    
                    <div className="order-details">
                      <div className="customer-info">
                        <strong>Customer Details:</strong><br />
                        Name: Unknown Customer<br />
                        Address: {order.address || 'No address'}
                      </div>
                      
                      {getOrderBadges(order, today).length > 0 && (
                        <div className="order-badges">
                          {getOrderBadges(order, today).map((badge, i) => (
                            <span key={i} className="badge">{badge}</span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Unassigned Orders Modal */}
        {showUnassigned && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h3>Add Orders to Route</h3>
                <button className="close-btn" onClick={() => setShowUnassigned(false)}>
                  <X size={20} />
                </button>
              </div>
              
              <div className="modal-body">
                <div className="selected-count">
                  {selectedOrders.size} orders selected
                </div>
                
                <div className="orders-list">
                  {unassignedOrders.map((order) => (
                    <div 
                      key={order.id} 
                      className={`selectable-order ${selectedOrders.has(order.id) ? 'selected' : ''}`}
                      onClick={() => toggleOrderSelection(order.id)}
                    >
                      <div className="order-checkbox">
                        {selectedOrders.has(order.id) && <CheckCircle size={16} />}
                      </div>
                      <div className="order-content">
                        <span className="order-code">#{order.orderNo}</span>
                        <span className="order-address">{order.address}</span>
                        {getOrderBadges(order, today).length > 0 && (
                          <div className="order-badges">
                            {getOrderBadges(order, today).map((badge, i) => (
                              <span key={i} className="badge small">{badge}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="modal-footer">
                <button 
                  className="btn-add"
                  onClick={handleAddOrders}
                  disabled={selectedOrders.size === 0 || addOrdersMutation.isPending}
                >
                  {addOrdersMutation.isPending ? 'Adding...' : `Add ${selectedOrders.size} Orders`}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Driver Selector Modal */}
        {showDriverSelector && (
          <div className="modal-overlay">
            <div className="modal">
              <div className="modal-header">
                <h3>Assign Drivers</h3>
                <button className="close-btn" onClick={() => setShowDriverSelector(false)}>
                  <X size={20} />
                </button>
              </div>
              
              <div className="modal-body">
                <div className="driver-section">
                  <h4>Primary Driver</h4>
                  <div className="current-driver">
                    Current: {driverNameById[selectedRoute.driverId || ''] || 'None'}
                  </div>
                  <div className="driver-list">
                    {drivers.map((driver) => (
                      <button
                        key={driver.id}
                        className="driver-btn"
                        onClick={() => handleAssignDriver(driver.id, false)}
                        disabled={updateRouteMutation.isPending}
                      >
                        {driver.name}
                      </button>
                    ))}
                  </div>
                </div>
                
                <div className="driver-section">
                  <h4>Secondary Driver (Optional)</h4>
                  <div className="current-driver">
                    Current: {selectedRoute.secondaryDriverId ? driverNameById[selectedRoute.secondaryDriverId] : 'None'}
                  </div>
                  <div className="driver-list">
                    <button
                      className="driver-btn"
                      onClick={() => handleAssignDriver('', true)}
                      disabled={updateRouteMutation.isPending}
                    >
                      Remove Secondary
                    </button>
                    {drivers.map((driver) => (
                      <button
                        key={driver.id}
                        className="driver-btn"
                        onClick={() => handleAssignDriver(driver.id, true)}
                        disabled={updateRouteMutation.isPending}
                      >
                        {driver.name}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        <style jsx>{`
          .mobile-container {
            min-height: 100vh;
            background: #f8fafc;
            max-width: 100vw;
            overflow-x: hidden;
          }
          
          .route-header {
            background: white;
            padding: 1rem;
            display: flex;
            align-items: center;
            gap: 1rem;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            position: sticky;
            top: 0;
            z-index: 10;
          }
          
          .back-btn {
            background: none;
            border: none;
            padding: 0.5rem;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #f1f5f9;
          }
          
          .route-info {
            flex: 1;
          }
          
          .route-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin: 0;
            color: #1e293b;
          }
          
          .route-meta {
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.25rem;
          }
          
          .secondary-driver {
            color: #8b5cf6;
            margin-left: 0.5rem;
          }
          
          .route-stats {
            background: white;
            padding: 1rem;
            margin: 1rem;
            border-radius: 12px;
            display: flex;
            justify-content: space-around;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
          }
          
          .stat-item {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            color: #64748b;
          }
          
          .action-buttons {
            padding: 0 1rem;
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
          }
          
          .action-btn {
            flex: 1;
            padding: 0.75rem;
            border-radius: 8px;
            border: none;
            font-size: 0.875rem;
            font-weight: 500;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0.5rem;
          }
          
          .action-btn.primary {
            background: #3b82f6;
            color: white;
          }
          
          .action-btn.secondary {
            background: white;
            color: #3b82f6;
            border: 1px solid #e2e8f0;
          }
          
          .orders-section {
            padding: 0 1rem 2rem;
          }
          
          .section-title {
            font-size: 1rem;
            font-weight: 600;
            color: #1e293b;
            margin-bottom: 1rem;
          }
          
          .loading-orders {
            text-align: center;
            color: #64748b;
            padding: 2rem;
          }
          
          .empty-state {
            text-align: center;
            padding: 3rem 1rem;
            color: #64748b;
          }
          
          .empty-state svg {
            color: #cbd5e1;
            margin-bottom: 1rem;
          }
          
          .add-first-btn {
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 0.875rem;
            margin-top: 1rem;
          }
          
          .orders-list {
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
          }
          
          .order-card {
            background: white;
            border-radius: 12px;
            padding: 1rem;
            box-shadow: 0 2px 8px rgba(0,0,0,0.05);
          }
          
          .order-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 0.75rem;
          }
          
          .order-info {
            display: flex;
            flex-direction: column;
            gap: 0.25rem;
          }
          
          .order-code {
            font-weight: 600;
            color: #1e293b;
          }
          
          .order-status {
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;
          }
          
          .remove-btn {
            background: #fee2e2;
            color: #dc2626;
            border: none;
            padding: 0.5rem;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
          }
          
          .order-details {
            font-size: 0.875rem;
            color: #64748b;
            line-height: 1.4;
          }
          
          .customer-info {
            margin-bottom: 0.75rem;
          }
          
          .order-badges {
            display: flex;
            flex-wrap: wrap;
            gap: 0.25rem;
          }
          
          .badge {
            background: #fef3c7;
            color: #92400e;
            padding: 0.125rem 0.5rem;
            border-radius: 4px;
            font-size: 0.75rem;
            font-weight: 500;
          }
          
          .badge.small {
            font-size: 0.625rem;
            padding: 0.125rem 0.375rem;
          }
          
          .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0,0,0,0.5);
            display: flex;
            align-items: flex-end;
            z-index: 50;
          }
          
          .modal {
            background: white;
            width: 100%;
            max-height: 90vh;
            border-radius: 16px 16px 0 0;
            overflow: hidden;
            display: flex;
            flex-direction: column;
          }
          
          .modal-header {
            padding: 1rem;
            border-bottom: 1px solid #e2e8f0;
            display: flex;
            justify-content: space-between;
            align-items: center;
          }
          
          .modal-header h3 {
            font-size: 1.125rem;
            font-weight: 600;
            margin: 0;
          }
          
          .close-btn {
            background: none;
            border: none;
            padding: 0.5rem;
            color: #64748b;
          }
          
          .modal-body {
            flex: 1;
            overflow-y: auto;
            padding: 1rem;
          }
          
          .selected-count {
            background: #eff6ff;
            color: #2563eb;
            padding: 0.5rem;
            border-radius: 6px;
            font-size: 0.875rem;
            text-align: center;
            margin-bottom: 1rem;
          }
          
          .selectable-order {
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 8px;
            padding: 0.75rem;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            cursor: pointer;
          }
          
          .selectable-order.selected {
            border-color: #3b82f6;
            background: #eff6ff;
          }
          
          .order-checkbox {
            width: 20px;
            height: 20px;
            border: 2px solid #d1d5db;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #3b82f6;
            margin-top: 2px;
          }
          
          .selectable-order.selected .order-checkbox {
            border-color: #3b82f6;
          }
          
          .order-content {
            flex: 1;
          }
          
          .order-address {
            display: block;
            font-size: 0.875rem;
            color: #64748b;
            margin-top: 0.25rem;
          }
          
          .modal-footer {
            padding: 1rem;
            border-top: 1px solid #e2e8f0;
          }
          
          .btn-add {
            width: 100%;
            background: #3b82f6;
            color: white;
            border: none;
            padding: 0.75rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 500;
          }
          
          .btn-add:disabled {
            background: #cbd5e1;
          }
          
          .driver-section {
            margin-bottom: 1.5rem;
          }
          
          .driver-section h4 {
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 0.5rem;
            color: #1e293b;
          }
          
          .current-driver {
            background: #f8fafc;
            padding: 0.5rem;
            border-radius: 6px;
            font-size: 0.875rem;
            color: #64748b;
            margin-bottom: 0.75rem;
          }
          
          .driver-list {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
          }
          
          .driver-btn {
            background: white;
            border: 1px solid #e2e8f0;
            padding: 0.75rem;
            border-radius: 8px;
            text-align: left;
            font-size: 0.875rem;
          }
          
          .driver-btn:active {
            background: #f1f5f9;
          }
        `}</style>
      </>
    );
  }

  // Main routes list view
  return (
    <>
      <Head>
        <title>Today&apos;s Routes - OrderOps</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, user-scalable=no" />
      </Head>

      <div className="mobile-container">
        {/* Header */}
        <div className="header">
          <h1 className="header-title">Today&apos;s Routes</h1>
          <div className="header-date">{new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'short', day: 'numeric' })}</div>
        </div>

        {/* Stats Row */}
        <div className="stats-row">
          <div className="stat">
            <div className="stat-value">{routes.length}</div>
            <div className="stat-label">Routes</div>
          </div>
          <div className="stat">
            <div className="stat-value">0</div>
            <div className="stat-label">Delivered</div>
          </div>
          <div className="stat">
            <div className="stat-value">{unassignedOrders.length}</div>
            <div className="stat-label">Unassigned</div>
          </div>
        </div>

        {/* Routes List */}
        <div className="routes-list">
          {routes.length === 0 ? (
            <div className="empty-state">
              <Truck size={48} />
              <h3>No routes for today</h3>
              <p>Routes will appear here when they are created</p>
            </div>
          ) : (
            routes.map((route) => (
              <div 
                key={route.id} 
                className="route-card"
                onClick={() => setSelectedRoute(route)}
              >
                <div className="route-card-header">
                  <div className="route-info">
                    <h3 className="route-name">{route.name}</h3>
                    <div className="route-driver">
                      <Users size={14} />
                      <span>{driverNameById[route.driverId || ''] || 'No Driver'}</span>
                      {route.secondaryDriverId && (
                        <span className="secondary">+ {driverNameById[route.secondaryDriverId]}</span>
                      )}
                    </div>
                  </div>
                  <div className="route-arrow">
                    <ArrowLeft size={16} style={{ transform: 'rotate(180deg)' }} />
                  </div>
                </div>
                
                <div className="route-stats-mini">
                  <div className="mini-stat">
                    <Package size={12} />
                    <span>{route.stops?.length || 0} stops</span>
                  </div>
                  <div className="mini-stat">
                    <MapPin size={12} />
                    <span>Ready</span>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {/* Desktop Redirect Modal */}
        {showDesktopRedirect && (
          <div className="desktop-redirect-overlay">
            <div className="desktop-redirect-modal">
              <div className="redirect-icon">🖥️</div>
              <h2>Desktop Version Available</h2>
              <p>
                This page is optimized for mobile devices. For the best desktop experience, 
                please use the full admin interface.
              </p>
              <div className="redirect-actions">
                <button className="btn-admin" onClick={handleGoToAdmin}>
                  Go to Admin Routes
                </button>
                <button 
                  className="btn-continue" 
                  onClick={() => setShowDesktopRedirect(false)}
                >
                  Continue Here
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .mobile-container {
          min-height: 100vh;
          background: #f8fafc;
          max-width: 100vw;
          overflow-x: hidden;
          padding-bottom: 2rem;
        }
        
        .header {
          background: linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%);
          color: white;
          padding: 2rem 1rem 1.5rem;
          position: sticky;
          top: 0;
          z-index: 10;
        }
        
        .header-title {
          font-size: 1.5rem;
          font-weight: 700;
          margin: 0;
        }
        
        .header-date {
          font-size: 0.875rem;
          opacity: 0.9;
          margin-top: 0.25rem;
        }
        
        .stats-row {
          background: white;
          margin: 1rem;
          padding: 1rem;
          border-radius: 12px;
          display: flex;
          justify-content: space-around;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
        }
        
        .stat {
          text-align: center;
        }
        
        .stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: #1e293b;
        }
        
        .stat-label {
          font-size: 0.75rem;
          color: #64748b;
          margin-top: 0.25rem;
        }
        
        .routes-list {
          padding: 0 1rem;
        }
        
        .empty-state {
          text-align: center;
          padding: 3rem 1rem;
          color: #64748b;
        }
        
        .empty-state svg {
          color: #cbd5e1;
          margin-bottom: 1rem;
        }
        
        .empty-state h3 {
          font-size: 1.125rem;
          font-weight: 600;
          margin: 1rem 0 0.5rem;
          color: #374151;
        }
        
        .empty-state p {
          font-size: 0.875rem;
          margin: 0;
        }
        
        .route-card {
          background: white;
          border-radius: 12px;
          padding: 1rem;
          margin-bottom: 0.75rem;
          box-shadow: 0 2px 8px rgba(0,0,0,0.05);
          cursor: pointer;
          transition: all 0.2s ease;
          border: 2px solid transparent;
        }
        
        .route-card:active {
          transform: scale(0.98);
          border-color: #3b82f6;
        }
        
        .route-card-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.75rem;
        }
        
        .route-name {
          font-size: 1rem;
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 0.5rem 0;
        }
        
        .route-driver {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          color: #64748b;
        }
        
        .secondary {
          color: #8b5cf6;
          font-size: 0.75rem;
        }
        
        .route-arrow {
          color: #cbd5e1;
        }
        
        .route-stats-mini {
          display: flex;
          gap: 1rem;
        }
        
        .mini-stat {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-size: 0.75rem;
          color: #64748b;
        }
        
        .desktop-redirect-overlay {
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(0, 0, 0, 0.7);
          display: flex;
          align-items: center;
          justify-content: center;
          z-index: 100;
          padding: 2rem;
        }
        
        .desktop-redirect-modal {
          background: white;
          border-radius: 16px;
          padding: 2rem;
          max-width: 400px;
          text-align: center;
          box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.1);
        }
        
        .redirect-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }
        
        .desktop-redirect-modal h2 {
          font-size: 1.5rem;
          font-weight: 600;
          color: #1e293b;
          margin: 0 0 1rem 0;
        }
        
        .desktop-redirect-modal p {
          color: #64748b;
          line-height: 1.6;
          margin: 0 0 2rem 0;
        }
        
        .redirect-actions {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }
        
        .btn-admin {
          background: #3b82f6;
          color: white;
          border: none;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 500;
          cursor: pointer;
          transition: background 0.2s ease;
        }
        
        .btn-admin:hover {
          background: #2563eb;
        }
        
        .btn-continue {
          background: none;
          color: #64748b;
          border: 1px solid #e2e8f0;
          padding: 0.75rem 1.5rem;
          border-radius: 8px;
          font-weight: 500;
          cursor: pointer;
          transition: all 0.2s ease;
        }
        
        .btn-continue:hover {
          background: #f8fafc;
          border-color: #cbd5e1;
        }
        
        @media (max-width: 380px) {
          .stats-row {
            padding: 0.75rem;
            margin: 0.75rem;
          }
          
          .stat-value {
            font-size: 1.25rem;
          }
          
          .route-card {
            padding: 0.75rem;
          }
          
          .header {
            padding: 1.5rem 0.75rem 1.25rem;
          }
          
          .desktop-redirect-overlay {
            padding: 1rem;
          }
          
          .desktop-redirect-modal {
            padding: 1.5rem;
          }
        }
      `}</style>
    </>
  );
}
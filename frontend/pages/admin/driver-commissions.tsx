import React from 'react';
import AdminLayout from '@/components/Layout/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  listDrivers, 
  listDriverOrders, 
  markSuccess, 
  updateCommission, 
  listUpsellRecords, 
  releaseUpsellIncentive,
  getInventoryConfig,
  getOrderUIDs
} from '@/lib/api';

export default function DriverCommissionsPage() {
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0, 7));
  const [activeTab, setActiveTab] = React.useState<'pending' | 'past-week' | 'previous' | 'upsells'>('pending');
  const [timeFilter, setTimeFilter] = React.useState<'current' | 'week' | 'month'>('current');
  const [message, setMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const qc = useQueryClient();
  
  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: listDrivers,
  });
  
  const ordersQuery = useQuery({
    queryKey: ['driver-orders', driverId, month],
    queryFn: () => (driverId ? listDriverOrders(Number(driverId), month) : Promise.resolve([])),
    enabled: !!driverId,
  });

  const upsellsQuery = useQuery({
    queryKey: ['upsell-records', driverId],
    queryFn: () => (driverId ? listUpsellRecords({ driver_id: Number(driverId) }) : Promise.resolve({ records: [] })),
    enabled: !!driverId,
  });

  const inventoryConfigQuery = useQuery({
    queryKey: ['inventory-config'],
    queryFn: getInventoryConfig,
  });

  const releaseCommissionMutation = useMutation({
    mutationFn: markSuccess,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] });
      setMessage({ type: 'success', text: 'Commission released successfully' });
      setTimeout(() => setMessage(null), 3000);
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to release commission' });
      setTimeout(() => setMessage(null), 3000);
    }
  });

  const updateCommissionMutation = useMutation({
    mutationFn: ({ orderId, amount }: { orderId: number; amount: number }) => 
      updateCommission(orderId, amount),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] });
      setMessage({ type: 'success', text: 'Commission updated successfully' });
      setTimeout(() => setMessage(null), 3000);
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to update commission' });
      setTimeout(() => setMessage(null), 3000);
    }
  });

  const releaseUpsellMutation = useMutation({
    mutationFn: releaseUpsellIncentive,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['upsell-records', driverId] });
      setMessage({ type: 'success', text: 'Upsell incentive released successfully' });
      setTimeout(() => setMessage(null), 3000);
    },
    onError: () => {
      setMessage({ type: 'error', text: 'Failed to release upsell incentive' });
      setTimeout(() => setMessage(null), 3000);
    }
  });

  const drivers = driversQuery.data || [];
  const orders = ordersQuery.data || [];
  const upsells = upsellsQuery.data?.records || [];
  const selectedDriver = drivers.find((d: any) => d.id == driverId);

  return (
    <div className="main">
      <div className="container">
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
            Driver Earnings
          </h1>
          <p style={{ opacity: 0.8 }}>
            Manage delivery commissions and upsell incentives
          </p>
        </div>

        {message && (
          <div
            style={{
              marginBottom: 'var(--space-6)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-2)',
              border: '1px solid',
              ...(message.type === 'success' 
                ? { background: '#f0fdf4', color: '#15803d', borderColor: '#bbf7d0' }
                : { background: '#fef2f2', color: '#dc2626', borderColor: '#fecaca' })
            }}
            role="alert"
          >
            {message.text}
          </div>
        )}

        <div className="card" style={{ marginBottom: 'var(--space-6)' }}>
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
            Select Driver & Month
          </h2>
          
          <div className="cluster" style={{ gap: 'var(--space-4)' }}>
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
                Driver
              </label>
              <select
                className="select"
                value={driverId}
                onChange={(e) => setDriverId(e.target.value)}
              >
                <option value="">Select driver...</option>
                {drivers.map((d: any) => (
                  <option key={d.id} value={d.id}>
                    {d.name || `Driver ${d.id}`}
                  </option>
                ))}
              </select>
            </div>
            
            <div>
              <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
                Month
              </label>
              <input
                className="input"
                type="month"
                value={month}
                onChange={(e) => setMonth(e.target.value)}
              />
            </div>
          </div>
        </div>

        {driverId && (
          <>
            {/* Tabs */}
            <div style={{ marginBottom: 'var(--space-4)' }}>
              <div style={{ borderBottom: '1px solid #e5e7eb' }}>
                <div style={{ display: 'flex', gap: 0, flexWrap: 'wrap' }}>
                  {[
                    { key: 'pending', label: 'Pending Verification', count: orders.filter((o: any) => !o.trip?.commission?.actualized_at).length },
                    { key: 'past-week', label: 'Past Week', count: orders.filter((o: any) => {
                      const weekAgo = new Date();
                      weekAgo.setDate(weekAgo.getDate() - 7);
                      return new Date(o.created_at) >= weekAgo;
                    }).length },
                    { key: 'previous', label: 'Previous Orders', count: orders.filter((o: any) => o.trip?.commission?.actualized_at).length },
                    { key: 'upsells', label: 'Upsell Incentives', count: upsells.length }
                  ].map(tab => (
                    <button
                      key={tab.key}
                      onClick={() => setActiveTab(tab.key as any)}
                      style={{
                        padding: 'var(--space-3) var(--space-4)',
                        border: 'none',
                        background: 'transparent',
                        borderBottom: activeTab === tab.key ? '2px solid #3b82f6' : '2px solid transparent',
                        color: activeTab === tab.key ? '#3b82f6' : '#6b7280',
                        fontWeight: activeTab === tab.key ? 600 : 500,
                        cursor: 'pointer',
                        fontSize: '0.875rem',
                        whiteSpace: 'nowrap'
                      }}
                    >
                      {tab.label} ({tab.count})
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Pending Verification Tab */}
            {activeTab === 'pending' && (
              <div className="card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  Pending Commission Verification - {selectedDriver?.name || `Driver ${driverId}`}
                </h2>
            
            {ordersQuery.isLoading && (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
                Loading orders...
              </div>
            )}

            {ordersQuery.isError && (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-error)' }}>
                Failed to load orders
              </div>
            )}

            {!ordersQuery.isLoading && orders.length === 0 && (
              <div style={{ padding: 'var(--space-8)', textAlign: 'center', opacity: 0.7 }}>
                No orders found for this driver and month
              </div>
            )}

            {!ordersQuery.isLoading && orders.length > 0 && (
              <div className="stack">
                {orders.filter((order: any) => 
                  order.trip?.status === 'DELIVERED' && !order.trip?.commission?.actualized_at
                ).map((order: any) => (
                  <EnhancedOrderCard 
                    key={order.id} 
                    order={order}
                    onRelease={(data: any) => releaseCommissionMutation.mutate(data)}
                    onMarkCashCollected={(data: any) => markCashCollectedMutation.mutate(data)}
                    isReleasing={releaseCommissionMutation.isPending}
                    isMarkingCash={markCashCollectedMutation.isPending}
                    inventoryConfig={inventoryConfigQuery.data}
                  />
                ))}
              </div>
            )}

            {/* Past Week Tab */}
            {activeTab === 'past-week' && (
              <div className="card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  Past Week Orders - {selectedDriver?.name || `Driver ${driverId}`}
                </h2>

                {!ordersQuery.isLoading && (
                  <div className="stack">
                    {orders.filter((order: any) => {
                      const weekAgo = new Date();
                      weekAgo.setDate(weekAgo.getDate() - 7);
                      return new Date(order.created_at) >= weekAgo;
                    }).map((order: any) => (
                      <OrderCard 
                        key={order.id} 
                        order={order}
                        onRelease={() => {}}
                        isReleasing={false}
                        onUpdateCommission={() => {}}
                        isUpdatingCommission={false}
                        showFullVerification={false}
                        readOnly={true}
                        inventoryConfig={inventoryConfigQuery.data}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Previous Orders Tab */}
            {activeTab === 'previous' && (
              <div className="card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  Previously Released - {selectedDriver?.name || `Driver ${driverId}`} - {month}
                </h2>

                {!ordersQuery.isLoading && (
                  <div className="stack">
                    {orders.filter((order: any) => order.trip?.commission?.actualized_at).map((order: any) => (
                      <OrderCard 
                        key={order.id} 
                        order={order}
                        onRelease={() => {}}
                        isReleasing={false}
                        onUpdateCommission={() => {}}
                        isUpdatingCommission={false}
                        readOnly={true}
                        inventoryConfig={inventoryConfigQuery.data}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Upsells Tab */}
            {activeTab === 'upsells' && (
              <div className="card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  Upsell Incentives - {selectedDriver?.name || `Driver ${driverId}`}
                </h2>
                
                {upsellsQuery.isLoading && (
                  <div style={{ padding: 'var(--space-8)', textAlign: 'center' }}>
                    Loading upsells...
                  </div>
                )}

                {upsellsQuery.isError && (
                  <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--color-error)' }}>
                    Failed to load upsells
                  </div>
                )}

                {!upsellsQuery.isLoading && upsells.length === 0 && (
                  <div style={{ padding: 'var(--space-8)', textAlign: 'center', opacity: 0.7 }}>
                    No upsell incentives found for this driver
                  </div>
                )}

                {!upsellsQuery.isLoading && upsells.length > 0 && (
                  <div className="stack">
                    {upsells.map((upsell: any) => (
                      <UpsellCard 
                        key={upsell.id} 
                        upsell={upsell}
                        onRelease={() => releaseUpsellMutation.mutate(upsell.id)}
                        isReleasing={releaseUpsellMutation.isPending}
                      />
                    ))}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        <div style={{
          marginTop: 'var(--space-6)',
          padding: 'var(--space-4)',
          background: 'linear-gradient(135deg, #eff6ff 0%, #f0f9ff 100%)',
          borderRadius: 'var(--radius-2)',
          border: '1px solid #bae6fd'
        }}>
          <h3 style={{ fontWeight: 600, color: '#0c4a6e', marginBottom: 'var(--space-3)', fontSize: '1.1rem' }}>
            🤖 AI-Powered Commission System (RM30 Flat Rate)
          </h3>
          <div className="stack" style={{ fontSize: '0.875rem', color: '#0c4a6e' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-4)' }}>
              <div>
                <p style={{ fontWeight: 600, marginBottom: 'var(--space-2)', color: '#1d4ed8' }}>📋 Automated Verification:</p>
                <ul style={{ margin: 0, paddingLeft: 'var(--space-4)' }}>
                  <li><strong>POD Photo Analysis</strong> - AI scans delivery photos</li>
                  <li><strong>Payment Detection</strong> - Identifies cash vs bank transfer</li>
                  <li><strong>Smart Cash Collection</strong> - Flags when cash retrieval needed</li>
                  <li><strong>Dual Driver Support</strong> - Automatic RM15 split for 2 drivers</li>
                </ul>
              </div>
              <div>
                <p style={{ fontWeight: 600, marginBottom: 'var(--space-2)', color: '#1d4ed8' }}>⚡ Release Options:</p>
                <ul style={{ margin: 0, paddingLeft: 'var(--space-4)' }}>
                  <li><strong>🤖 AI Release</strong> - 70% confidence auto-approval</li>
                  <li><strong>💰 Cash Confirmation</strong> - For cash payment orders</li>
                  <li><strong>⚠️ Manual Override</strong> - Skip AI for edge cases</li>
                  <li><strong>📊 All Activity</strong> - View pending across all drivers</li>
                </ul>
              </div>
            </div>
            
            <div style={{ 
              marginTop: 'var(--space-3)', 
              padding: 'var(--space-3)', 
              background: 'rgba(59, 130, 246, 0.1)', 
              borderRadius: 'var(--radius-1)',
              border: '1px solid rgba(59, 130, 246, 0.2)'
            }}>
              <p style={{ margin: 0, fontWeight: 500 }}>
                <strong>🎯 How it works:</strong> When an order is DELIVERED, AI analyzes POD photos to detect payment method. 
                For <strong>cash payments</strong>, system requires confirmation that cash was collected from driver before releasing commission. 
                For <strong>bank transfers</strong>, commission releases automatically. 
                <strong>30% of cases</strong> still require manual review for quality assurance.
              </p>
            </div>
            
            <div style={{ 
              marginTop: 'var(--space-2)',
              fontSize: '0.75rem',
              opacity: 0.8,
              fontStyle: 'italic',
              textAlign: 'center'
            }}>
              💡 Trip status changes: DELIVERED → SUCCESS (after commission release) | 
              Commission entries: EARNED → PAID
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function OrderCard({ 
  order, 
  onRelease, 
  isReleasing,
  onUpdateCommission,
  isUpdatingCommission,
  showFullVerification = false,
  readOnly = false,
  inventoryConfig
}: { 
  order: any; 
  onRelease: () => void;
  isReleasing: boolean;
  onUpdateCommission: (amount: number) => void;
  isUpdatingCommission: boolean;
  showFullVerification?: boolean;
  readOnly?: boolean;
  inventoryConfig?: any;
}) {
  const [showPodPhotos, setShowPodPhotos] = React.useState(false);
  const [showUidDetails, setShowUidDetails] = React.useState(false);
  const [commissionAmount, setCommissionAmount] = React.useState('');
  
  // Fetch UID data (inventory config is already available from parent scope)
  
  const orderUidsQuery = useQuery({
    queryKey: ['order-uids', order.id],
    queryFn: () => getOrderUIDs(order.id),
    enabled: inventoryConfig?.uid_inventory_enabled === true,
  });
  
  const trip = order.trip || {};
  const currentCommission = trip.commission?.computed_amount || order.commission || 0;
  const podPhotos = trip.pod_photo_urls || (trip.pod_photo_url ? [trip.pod_photo_url] : []);
  const hasPodPhoto = podPhotos.length > 0;
  const isDelivered = trip.status === 'DELIVERED'; // Check trip status, not order status
  const paymentCollected = order.payment_status === 'PAID' || order.total_paid > 0; // Check if initial payment collected
  const hasUpsells = (order.upsell_amount || 0) > 0; // Check for upsells
  const isReleased = trip.commission?.actualized_at; // Check if already released
  
  // UID verification (if inventory system enabled)
  const inventoryEnabled = inventoryConfig?.uid_inventory_enabled === true;
  const uidData = orderUidsQuery.data;
  const hasUidScans = inventoryEnabled && uidData && uidData.uids && uidData.uids.length > 0;
  const uidScanRequired = inventoryEnabled && inventoryConfig?.uid_scan_required_after_pod === true;
  
  // Enhanced verification includes UID scanning if required
  const uidVerificationPassed = !uidScanRequired || hasUidScans;
  
  // Full verification requires all steps (with UID if enabled and required)
  const canRelease = isDelivered && hasPodPhoto && paymentCollected && currentCommission > 0 && !isReleased && uidVerificationPassed;
  
  // Initialize commission amount from current commission
  React.useEffect(() => {
    if (currentCommission > 0) {
      setCommissionAmount(currentCommission.toString());
    } else {
      setCommissionAmount('30'); // Default commission amount
    }
  }, [currentCommission]);

  const handleCommissionChange = () => {
    const amount = Number(commissionAmount);
    if (amount > 0) {
      onUpdateCommission(amount);
    }
  };

  return (
    <div style={{
      padding: 'var(--space-4)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-2)',
      background: 'var(--color-background)'
    }}>
      {/* Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-1)', margin: 0 }}>
            Order #{order.code || order.id}
          </h3>
          <div className="cluster" style={{ gap: 'var(--space-2)', fontSize: '0.875rem' }}>
            <span style={{ 
              padding: '0.125rem 0.5rem', 
              borderRadius: 'var(--radius-1)',
              background: isDelivered ? '#dcfce7' : '#fef3c7',
              color: isDelivered ? '#15803d' : '#d97706'
            }}>
              {trip.status || order.status}
            </span>
            {hasPodPhoto && (
              <button
                onClick={() => setShowPodPhotos(!showPodPhotos)}
                style={{ 
                  padding: '0.125rem 0.5rem', 
                  borderRadius: 'var(--radius-1)',
                  background: '#dcfce7',
                  color: '#15803d',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                📸 {showPodPhotos ? 'Hide' : 'View'} POD ({podPhotos.length})
              </button>
            )}
            {inventoryEnabled && hasUidScans && (
              <button
                onClick={() => setShowUidDetails(!showUidDetails)}
                style={{ 
                  padding: '0.125rem 0.5rem', 
                  borderRadius: 'var(--radius-1)',
                  background: '#dbeafe',
                  color: '#1d4ed8',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                🏷️ {showUidDetails ? 'Hide' : 'View'} UIDs ({uidData?.uids?.length || 0})
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Commission Input Row */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', marginBottom: 'var(--space-3)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flex: 1 }}>
          <label style={{ fontSize: '0.875rem', fontWeight: 500, minWidth: '80px' }}>
            Commission:
          </label>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
            <span style={{ fontSize: '0.875rem' }}>RM</span>
            <input
              type="number"
              min="0"
              step="0.01"
              value={commissionAmount}
              onChange={(e) => setCommissionAmount(e.target.value)}
              onBlur={handleCommissionChange}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  handleCommissionChange();
                }
              }}
              style={{
                width: '80px',
                padding: '0.25rem 0.5rem',
                border: '1px solid #d1d5db',
                borderRadius: 'var(--radius-1)',
                fontSize: '0.875rem',
                background: readOnly ? '#f9fafb' : 'white'
              }}
              disabled={isUpdatingCommission || readOnly}
              readOnly={readOnly}
            />
            {isUpdatingCommission && <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Saving...</span>}
          </div>
        </div>

        {!readOnly && (
          <button
            onClick={(e) => {
              e.preventDefault();
              if (canRelease) {
                const confirmed = window.confirm(
                  `Release commission of RM ${currentCommission.toFixed(2)} to driver?\n\nThis action cannot be undone.`
                );
                if (confirmed) {
                  onRelease();
                }
              }
            }}
            disabled={!canRelease || isReleasing}
            style={{
              background: canRelease && !isReleasing ? '#10b981' : '#9ca3af',
              color: 'white',
              border: 'none',
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-2)',
              fontSize: '0.875rem',
              cursor: canRelease && !isReleasing ? 'pointer' : 'not-allowed',
              fontWeight: '500',
              minWidth: '140px'
            }}
            title={!canRelease ? 'Complete all verification steps to release commission' : 'Release commission to driver'}
          >
            {isReleasing ? 'Releasing...' : isReleased ? 'Already Released' : 'Enter & Release'}
          </button>
        )}
      </div>

      {/* Verification Steps */}
      {showFullVerification && (
        <div style={{ 
          marginBottom: 'var(--space-3)', 
          padding: 'var(--space-3)', 
          background: '#f8fafc', 
          borderRadius: 'var(--radius-1)',
          border: '1px solid #e2e8f0'
        }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            Commission Verification Checklist
          </h4>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-2)', fontSize: '0.875rem' }}>
            <span style={{ color: isDelivered ? '#15803d' : '#dc2626' }}>
              {isDelivered ? '✅' : '❌'} 1. Order Delivered
            </span>
            <span style={{ color: hasPodPhoto ? '#15803d' : '#dc2626' }}>
              {hasPodPhoto ? '✅' : '❌'} 2. POD Available & Correct
            </span>
            <span style={{ color: paymentCollected ? '#15803d' : '#dc2626' }}>
              {paymentCollected ? '✅' : '❌'} 3. Initial Payment Collected
            </span>
            {inventoryEnabled && uidScanRequired && (
              <span style={{ color: hasUidScans ? '#15803d' : '#dc2626' }}>
                {hasUidScans ? '✅' : '❌'} 4. UID Scanning Complete
              </span>
            )}
            <span style={{ color: hasUpsells ? '#f59e0b' : '#6b7280' }}>
              {hasUpsells ? '💰' : '➖'} {inventoryEnabled && uidScanRequired ? '5' : '4'}. Upsells: {hasUpsells ? `RM ${(order.upsell_amount || 0).toFixed(2)}` : 'None'}
            </span>
          </div>
        </div>
      )}

      {/* Status Indicators */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', fontSize: '0.875rem', flexWrap: 'wrap' }}>
        <span style={{ color: isDelivered ? '#15803d' : '#6b7280' }}>
          {isDelivered ? '✅' : '⏳'} Delivered
        </span>
        <span style={{ color: hasPodPhoto ? '#15803d' : '#d97706' }}>
          {hasPodPhoto ? '✅' : '⚠️'} POD Photo
        </span>
        <span style={{ color: paymentCollected ? '#15803d' : '#dc2626' }}>
          {paymentCollected ? '✅' : '❌'} Payment Collected
        </span>
        {inventoryEnabled && uidScanRequired && (
          <span style={{ color: hasUidScans ? '#15803d' : '#dc2626' }}>
            {hasUidScans ? '✅' : '❌'} UID Scanned
          </span>
        )}
        <span style={{ color: currentCommission > 0 ? '#15803d' : '#6b7280' }}>
          {currentCommission > 0 ? '✅' : '⏳'} Commission Set
        </span>
        {isReleased && (
          <span style={{ color: '#15803d' }}>
            ✅ Released {new Date(isReleased).toLocaleDateString()}
          </span>
        )}
      </div>

      {showPodPhotos && podPhotos.length > 0 && (
        <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-4)', background: '#f9fafb', borderRadius: 'var(--radius-2)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            Proof of Delivery Photos
          </h4>
          <div className="cluster" style={{ gap: 'var(--space-2)' }}>
            {podPhotos.map((url: string, index: number) => (
              <div key={index} style={{ position: 'relative' }}>
                <img
                  src={url}
                  alt={`POD Photo ${index + 1}`}
                  style={{
                    width: '120px',
                    height: '120px',
                    objectFit: 'cover',
                    borderRadius: 'var(--radius-2)',
                    border: '1px solid #d1d5db',
                    cursor: 'pointer'
                  }}
                  onClick={() => window.open(url, '_blank')}
                />
                <div style={{
                  position: 'absolute',
                  top: '4px',
                  right: '4px',
                  background: 'rgba(0,0,0,0.7)',
                  color: 'white',
                  fontSize: '0.75rem',
                  padding: '2px 6px',
                  borderRadius: '12px'
                }}>
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 'var(--space-2)' }}>
            Click on any photo to view full size
          </p>
        </div>
      )}

      {showUidDetails && inventoryEnabled && uidData && uidData.uids && uidData.uids.length > 0 && (
        <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-4)', background: '#f8fafc', borderRadius: 'var(--radius-2)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            UID Scan History
          </h4>
          <div style={{ marginBottom: 'var(--space-3)', fontSize: '0.875rem', color: '#6b7280' }}>
            Total: {uidData.uids.length} scans • 
            Issued: {uidData.total_issued || 0} • 
            Returned: {uidData.total_returned || 0}
          </div>
          <div className="stack" style={{ gap: 'var(--space-2)' }}>
            {uidData.uids.map((uid: any, index: number) => (
              <div key={index} style={{
                padding: 'var(--space-2)',
                background: 'white',
                borderRadius: 'var(--radius-1)',
                border: '1px solid #e5e7eb',
                fontSize: '0.75rem'
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 'var(--space-1)' }}>
                  <strong style={{ fontFamily: 'monospace' }}>{uid.uid}</strong>
                  <span style={{
                    padding: '0.125rem 0.375rem',
                    borderRadius: 'var(--radius-1)',
                    fontSize: '0.625rem',
                    fontWeight: 600,
                    background: uid.action === 'DELIVER' ? '#dcfce7' : uid.action === 'LOAD_OUT' ? '#dbeafe' : '#fef3c7',
                    color: uid.action === 'DELIVER' ? '#15803d' : uid.action === 'LOAD_OUT' ? '#1d4ed8' : '#d97706'
                  }}>
                    {uid.action}
                  </span>
                </div>
                <div style={{ color: '#6b7280' }}>
                  {uid.sku_name && <div>{uid.sku_name}</div>}
                  <div>{uid.driver_name} • {new Date(uid.scanned_at).toLocaleString()}</div>
                  {uid.notes && <div style={{ fontStyle: 'italic' }}>{uid.notes}</div>}
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 'var(--space-2)' }}>
            UID scanning provides detailed inventory tracking for enhanced delivery verification
          </p>
        </div>
      )}
    </div>
  );
}

function UpsellCard({ 
  upsell, 
  onRelease, 
  isReleasing 
}: { 
  upsell: any; 
  onRelease: () => void;
  isReleasing: boolean;
}) {
  const isPending = upsell.incentive_status === 'PENDING';
  const canRelease = isPending && upsell.driver_incentive > 0;

  return (
    <div style={{
      padding: 'var(--space-4)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-2)',
      background: 'var(--color-background)'
    }}>
      {/* Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-1)', margin: 0 }}>
            Order #{upsell.order_code}
          </h3>
          <div className="cluster" style={{ gap: 'var(--space-2)', fontSize: '0.875rem' }}>
            <span style={{ 
              padding: '0.125rem 0.5rem', 
              borderRadius: 'var(--radius-1)',
              background: isPending ? '#fef3c7' : '#dcfce7',
              color: isPending ? '#d97706' : '#15803d'
            }}>
              {isPending ? 'Pending' : 'Released'}
            </span>
            <span style={{ color: '#6b7280' }}>
              {new Date(upsell.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
      </div>

      {/* Upsell Details */}
      <div style={{ marginBottom: 'var(--space-3)' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', fontSize: '0.875rem' }}>
          <div>
            <span style={{ color: '#6b7280' }}>Upsell Amount:</span>
            <div style={{ fontWeight: 600 }}>RM {Number(upsell.upsell_amount).toFixed(2)}</div>
          </div>
          <div>
            <span style={{ color: '#6b7280' }}>Your Incentive (10%):</span>
            <div style={{ fontWeight: 600, color: '#10b981' }}>RM {Number(upsell.driver_incentive).toFixed(2)}</div>
          </div>
        </div>
      </div>

      {/* Items Upsold */}
      {upsell.items_upsold && upsell.items_upsold.length > 0 && (
        <div style={{ marginBottom: 'var(--space-3)' }}>
          <div style={{ fontSize: '0.875rem', color: '#6b7280', marginBottom: 'var(--space-1)' }}>Items Upsold:</div>
          <div style={{ fontSize: '0.75rem' }}>
            {upsell.items_upsold.map((item: any, index: number) => (
              <div key={index} style={{ marginBottom: 'var(--space-1)' }}>
                <strong>{item.new_name}</strong> ({item.upsell_type}): 
                RM {Number(item.original_price).toFixed(2)} → RM {Number(item.new_price).toFixed(2)}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notes */}
      {upsell.upsell_notes && (
        <div style={{ marginBottom: 'var(--space-3)', fontSize: '0.875rem' }}>
          <span style={{ color: '#6b7280' }}>Notes: </span>
          {upsell.upsell_notes}
        </div>
      )}

      {/* Action Button */}
      <button
        onClick={(e) => {
          e.preventDefault();
          onRelease();
        }}
        disabled={!canRelease || isReleasing}
        style={{
          background: canRelease && !isReleasing ? '#10b981' : '#9ca3af',
          color: 'white',
          border: 'none',
          padding: '0.5rem 1rem',
          borderRadius: 'var(--radius-1)',
          fontSize: '0.875rem',
          cursor: canRelease && !isReleasing ? 'pointer' : 'not-allowed'
        }}
      >
        {isReleasing ? 'Releasing...' : canRelease ? 'Release Incentive' : isPending ? 'Pending Review' : 'Already Released'}
      </button>
    </div>
  );
}

// AI-Enhanced Order Card with commission release functionality
function EnhancedOrderCard({ 
  order, 
  onRelease,
  onMarkCashCollected,
  isReleasing,
  isMarkingCash,
  inventoryConfig
}: { 
  order: any;
  onRelease: (data: any) => void;
  onMarkCashCollected: (data: any) => void;
  isReleasing: boolean;
  isMarkingCash: boolean;
  inventoryConfig?: any;
}) {
  const [showPodPhotos, setShowPodPhotos] = React.useState(false);
  const [showAiAnalysis, setShowAiAnalysis] = React.useState(false);
  const [releaseNotes, setReleaseNotes] = React.useState('');
  const [aiAnalysis, setAiAnalysis] = React.useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);

  const trip = order.trip || {};
  const tripId = trip.id;
  const podPhotos = trip.pod_photo_urls || (trip.pod_photo_url ? [trip.pod_photo_url] : []);
  const hasPodPhoto = podPhotos.length > 0;
  const isDelivered = trip.status === 'DELIVERED';
  const paymentCollected = order.payment_status === 'PAID' || order.total_paid > 0;
  const isReleased = trip.status === 'SUCCESS';

  // AI Analysis function
  const runAiAnalysis = React.useCallback(async () => {
    if (!tripId || isAnalyzing) return;
    
    setIsAnalyzing(true);
    try {
      const result = await analyzeCommissionEligibility(tripId);
      setAiAnalysis(result);
      setShowAiAnalysis(true);
    } catch (error: any) {
      console.error('AI analysis failed:', error);
      setAiAnalysis({ 
        error: true, 
        message: error.message || 'AI analysis failed - manual verification required' 
      });
    } finally {
      setIsAnalyzing(false);
    }
  }, [tripId, isAnalyzing]);

  const handleRelease = (manualOverride = false, cashCollected = false) => {
    onRelease({
      trip_id: tripId,
      manual_override: manualOverride,
      cash_collected: cashCollected,
      notes: releaseNotes
    });
  };

  const handleMarkCashCollected = () => {
    onMarkCashCollected({
      tripId: tripId,
      notes: releaseNotes || 'Cash collected confirmation'
    });
  };

  return (
    <div style={{
      padding: 'var(--space-4)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-2)',
      background: 'var(--color-background)'
    }}>
      {/* Header Row */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-1)', margin: 0 }}>
            Order #{order.code || order.id} {trip.has_dual_drivers ? '(Dual Driver)' : ''}
          </h3>
          <div className="cluster" style={{ gap: 'var(--space-2)', fontSize: '0.875rem' }}>
            <span style={{ 
              padding: '0.125rem 0.5rem', 
              borderRadius: 'var(--radius-1)',
              background: isDelivered ? '#dcfce7' : isReleased ? '#dbeafe' : '#fef3c7',
              color: isDelivered ? '#15803d' : isReleased ? '#1d4ed8' : '#d97706'
            }}>
              {trip.status || 'UNKNOWN'}
            </span>
            {hasPodPhoto && (
              <button
                onClick={() => setShowPodPhotos(!showPodPhotos)}
                style={{ 
                  padding: '0.125rem 0.5rem', 
                  borderRadius: 'var(--radius-1)',
                  background: '#dcfce7',
                  color: '#15803d',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: '0.875rem'
                }}
              >
                📸 {showPodPhotos ? 'Hide' : 'View'} POD ({podPhotos.length})
              </button>
            )}
          </div>
        </div>
        
        {/* AI Analysis Button */}
        {isDelivered && !isReleased && (
          <button
            onClick={runAiAnalysis}
            disabled={isAnalyzing}
            style={{
              padding: '0.5rem 1rem',
              borderRadius: 'var(--radius-2)',
              border: '1px solid #3b82f6',
              background: isAnalyzing ? '#f3f4f6' : '#eff6ff',
              color: '#1d4ed8',
              fontSize: '0.875rem',
              cursor: isAnalyzing ? 'not-allowed' : 'pointer',
              fontWeight: '500'
            }}
          >
            {isAnalyzing ? '🔄 Analyzing...' : '🤖 AI Analysis'}
          </button>
        )}
      </div>

      {/* Customer & Order Details */}
      <div style={{ marginBottom: 'var(--space-3)', fontSize: '0.875rem', color: '#6b7280' }}>
        <div><strong>Customer:</strong> {order.customer_name}</div>
        <div><strong>Amount:</strong> RM {Number(order.total || 0).toFixed(2)}</div>
        {trip.delivered_at && (
          <div><strong>Delivered:</strong> {new Date(trip.delivered_at).toLocaleString()}</div>
        )}
      </div>

      {/* AI Analysis Results */}
      {aiAnalysis && showAiAnalysis && (
        <div style={{
          marginBottom: 'var(--space-4)',
          padding: 'var(--space-4)',
          background: aiAnalysis.error ? '#fef2f2' : '#f0f9ff',
          border: `1px solid ${aiAnalysis.error ? '#fecaca' : '#bae6fd'}`,
          borderRadius: 'var(--radius-2)'
        }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            🤖 AI Payment Analysis {!aiAnalysis.error && `(${Math.round(aiAnalysis.ai_verification?.confidence_score * 100 || 0)}% confidence)`}
          </h4>
          
          {aiAnalysis.error ? (
            <p style={{ color: '#dc2626', fontSize: '0.875rem' }}>
              {aiAnalysis.message}
            </p>
          ) : (
            <div style={{ fontSize: '0.875rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-3)', marginBottom: 'var(--space-2)' }}>
                <div>
                  <strong>Payment Method:</strong> 
                  <span style={{
                    marginLeft: 'var(--space-1)',
                    padding: '0.125rem 0.375rem',
                    borderRadius: 'var(--radius-1)',
                    fontSize: '0.75rem',
                    fontWeight: 600,
                    background: aiAnalysis.ai_verification?.payment_method === 'cash' ? '#fef3c7' : '#dcfce7',
                    color: aiAnalysis.ai_verification?.payment_method === 'cash' ? '#d97706' : '#15803d'
                  }}>
                    {aiAnalysis.ai_verification?.payment_method?.toUpperCase() || 'UNKNOWN'}
                  </span>
                </div>
                <div>
                  <strong>Cash Collection Required:</strong> 
                  <span style={{ color: aiAnalysis.ai_verification?.cash_collection_required ? '#dc2626' : '#15803d' }}>
                    {aiAnalysis.ai_verification?.cash_collection_required ? ' Yes' : ' No'}
                  </span>
                </div>
              </div>
              
              {aiAnalysis.ai_verification?.analysis_details && (
                <div style={{ fontSize: '0.75rem', color: '#6b7280', fontStyle: 'italic' }}>
                  <strong>Analysis:</strong> {aiAnalysis.ai_verification.analysis_details}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Commission Release Actions */}
      {isDelivered && !isReleased && (
        <div style={{
          marginBottom: 'var(--space-3)',
          padding: 'var(--space-3)',
          background: '#f8fafc',
          borderRadius: 'var(--radius-1)',
          border: '1px solid #e2e8f0'
        }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            Commission Release (RM30 flat rate)
          </h4>
          
          <div style={{ marginBottom: 'var(--space-3)' }}>
            <label style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
              Notes (optional):
            </label>
            <textarea
              value={releaseNotes}
              onChange={(e) => setReleaseNotes(e.target.value)}
              placeholder="Add any notes about the commission release..."
              style={{
                width: '100%',
                minHeight: '60px',
                padding: 'var(--space-2)',
                border: '1px solid #d1d5db',
                borderRadius: 'var(--radius-1)',
                fontSize: '0.875rem',
                resize: 'vertical'
              }}
            />
          </div>
          
          <div className="cluster" style={{ gap: 'var(--space-2)' }}>
            {/* Auto Release Button */}
            <button
              onClick={() => handleRelease(false, false)}
              disabled={!hasPodPhoto || isReleasing || isMarkingCash}
              style={{
                background: hasPodPhoto && !isReleasing ? '#10b981' : '#9ca3af',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-2)',
                fontSize: '0.875rem',
                cursor: hasPodPhoto && !isReleasing ? 'pointer' : 'not-allowed',
                fontWeight: '500'
              }}
              title={!hasPodPhoto ? 'POD photo required' : 'Release with AI verification'}
            >
              {isReleasing ? '🔄 Releasing...' : '🤖 AI Release'}
            </button>
            
            {/* Cash Collection Button */}
            {aiAnalysis?.ai_verification?.cash_collection_required && (
              <button
                onClick={handleMarkCashCollected}
                disabled={isMarkingCash || isReleasing}
                style={{
                  background: '#f59e0b',
                  color: 'white',
                  border: 'none',
                  padding: '0.5rem 1rem',
                  borderRadius: 'var(--radius-2)',
                  fontSize: '0.875rem',
                  cursor: isMarkingCash ? 'not-allowed' : 'pointer',
                  fontWeight: '500'
                }}
              >
                {isMarkingCash ? '💰 Confirming...' : '💰 Confirm Cash Collected'}
              </button>
            )}
            
            {/* Manual Override Button */}
            <button
              onClick={() => {
                const confirmed = window.confirm(
                  'Manual override will bypass AI verification.\n\nAre you sure you want to proceed?'
                );
                if (confirmed) {
                  handleRelease(true, true);
                }
              }}
              disabled={isReleasing || isMarkingCash}
              style={{
                background: '#6b7280',
                color: 'white',
                border: 'none',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-2)',
                fontSize: '0.875rem',
                cursor: isReleasing || isMarkingCash ? 'not-allowed' : 'pointer',
                fontWeight: '500'
              }}
            >
              ⚠️ Manual Override
            </button>
          </div>
        </div>
      )}

      {/* Status Indicators */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', fontSize: '0.875rem', flexWrap: 'wrap' }}>
        <span style={{ color: isDelivered ? '#15803d' : '#6b7280' }}>
          {isDelivered ? '✅' : '⏳'} Delivered
        </span>
        <span style={{ color: hasPodPhoto ? '#15803d' : '#d97706' }}>
          {hasPodPhoto ? '✅' : '⚠️'} POD Photo ({podPhotos.length})
        </span>
        <span style={{ color: paymentCollected ? '#15803d' : '#dc2626' }}>
          {paymentCollected ? '✅' : '❌'} Payment Collected
        </span>
        {isReleased && (
          <span style={{ color: '#1d4ed8', fontWeight: 600 }}>
            ✅ Commission Released
          </span>
        )}
      </div>

      {/* POD Photos Display */}
      {showPodPhotos && podPhotos.length > 0 && (
        <div style={{ marginTop: 'var(--space-4)', padding: 'var(--space-4)', background: '#f9fafb', borderRadius: 'var(--radius-2)' }}>
          <h4 style={{ fontSize: '0.875rem', fontWeight: 600, marginBottom: 'var(--space-2)', color: '#374151' }}>
            📸 Proof of Delivery & Payment Photos
          </h4>
          <div className="cluster" style={{ gap: 'var(--space-2)' }}>
            {podPhotos.map((url: string, index: number) => (
              <div key={index} style={{ position: 'relative' }}>
                <img
                  src={url}
                  alt={`POD/Payment Photo ${index + 1}`}
                  style={{
                    width: '120px',
                    height: '120px',
                    objectFit: 'cover',
                    borderRadius: 'var(--radius-2)',
                    border: '1px solid #d1d5db',
                    cursor: 'pointer'
                  }}
                  onClick={() => window.open(url, '_blank')}
                />
                <div style={{
                  position: 'absolute',
                  top: '4px',
                  right: '4px',
                  background: 'rgba(0,0,0,0.7)',
                  color: 'white',
                  fontSize: '0.75rem',
                  padding: '2px 6px',
                  borderRadius: '12px'
                }}>
                  {index + 1}
                </div>
              </div>
            ))}
          </div>
          <p style={{ fontSize: '0.75rem', color: '#6b7280', marginTop: 'var(--space-2)' }}>
            💡 Click on any photo to view full size. AI analyzes these photos to detect payment method.
          </p>
        </div>
      )}
    </div>
  );
}

// Pending Commission Card for cross-driver overview
function PendingCommissionCard({ 
  commission, 
  drivers,
  onRelease,
  onMarkCashCollected,
  isReleasing,
  isMarkingCash
}: { 
  commission: any;
  drivers: any[];
  onRelease: (data: any) => void;
  onMarkCashCollected: (data: any) => void;
  isReleasing: boolean;
  isMarkingCash: boolean;
}) {
  const [showDetails, setShowDetails] = React.useState(false);
  const [releaseNotes, setReleaseNotes] = React.useState('');
  const [aiAnalysis, setAiAnalysis] = React.useState<any>(null);
  const [isAnalyzing, setIsAnalyzing] = React.useState(false);

  const primaryDriver = drivers.find(d => d.id === commission.primary_driver_id);
  const secondaryDriver = commission.secondary_driver_id ? 
    drivers.find(d => d.id === commission.secondary_driver_id) : null;

  const runAiAnalysis = async () => {
    if (!commission.trip_id || isAnalyzing) return;
    
    setIsAnalyzing(true);
    try {
      const result = await analyzeCommissionEligibility(commission.trip_id);
      setAiAnalysis(result);
    } catch (error: any) {
      console.error('AI analysis failed:', error);
      setAiAnalysis({ 
        error: true, 
        message: error.message || 'AI analysis failed' 
      });
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRelease = (manualOverride = false, cashCollected = false) => {
    onRelease({
      trip_id: commission.trip_id,
      manual_override: manualOverride,
      cash_collected: cashCollected,
      notes: releaseNotes
    });
  };

  return (
    <div style={{
      padding: 'var(--space-4)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-2)',
      background: 'var(--color-background)'
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-1)', margin: 0 }}>
            Order #{commission.order_code}
          </h3>
          <div style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            <div><strong>Customer:</strong> {commission.customer_name}</div>
            <div><strong>Amount:</strong> RM {Number(commission.total_amount).toFixed(2)}</div>
            <div><strong>Primary Driver:</strong> {primaryDriver?.name || `Driver ${commission.primary_driver_id}`}</div>
            {secondaryDriver && (
              <div><strong>Secondary Driver:</strong> {secondaryDriver.name}</div>
            )}
            <div><strong>Delivered:</strong> {commission.delivered_at ? 
              new Date(commission.delivered_at).toLocaleString() : 'Recently'}
            </div>
          </div>
        </div>
        
        <div className="cluster" style={{ gap: 'var(--space-2)' }}>
          <span style={{
            padding: '0.125rem 0.5rem',
            borderRadius: 'var(--radius-1)',
            background: commission.has_pod_photos ? '#dcfce7' : '#fef3c7',
            color: commission.has_pod_photos ? '#15803d' : '#d97706',
            fontSize: '0.75rem',
            fontWeight: 600
          }}>
            {commission.has_pod_photos ? '✅ POD' : '⚠️ No POD'} ({commission.pod_photo_count})
          </span>
          
          <button
            onClick={runAiAnalysis}
            disabled={isAnalyzing}
            style={{
              padding: '0.25rem 0.5rem',
              borderRadius: 'var(--radius-1)',
              border: '1px solid #3b82f6',
              background: isAnalyzing ? '#f3f4f6' : '#eff6ff',
              color: '#1d4ed8',
              fontSize: '0.75rem',
              cursor: isAnalyzing ? 'not-allowed' : 'pointer',
              fontWeight: '500'
            }}
          >
            {isAnalyzing ? '🔄' : '🤖'}
          </button>
        </div>
      </div>

      {/* AI Analysis Results */}
      {aiAnalysis && (
        <div style={{
          marginBottom: 'var(--space-3)',
          padding: 'var(--space-3)',
          background: aiAnalysis.error ? '#fef2f2' : '#f0f9ff',
          border: `1px solid ${aiAnalysis.error ? '#fecaca' : '#bae6fd'}`,
          borderRadius: 'var(--radius-1)',
          fontSize: '0.875rem'
        }}>
          {aiAnalysis.error ? (
            <p style={{ color: '#dc2626' }}>
              🚨 {aiAnalysis.message}
            </p>
          ) : (
            <div>
              <strong>Payment Method:</strong> 
              <span style={{
                marginLeft: 'var(--space-1)',
                padding: '0.125rem 0.375rem',
                borderRadius: 'var(--radius-1)',
                fontSize: '0.75rem',
                fontWeight: 600,
                background: aiAnalysis.ai_verification?.payment_method === 'cash' ? '#fef3c7' : '#dcfce7',
                color: aiAnalysis.ai_verification?.payment_method === 'cash' ? '#d97706' : '#15803d'
              }}>
                {aiAnalysis.ai_verification?.payment_method?.toUpperCase() || 'UNKNOWN'}
              </span>
              {aiAnalysis.ai_verification?.cash_collection_required && (
                <span style={{ color: '#dc2626', marginLeft: 'var(--space-2)', fontSize: '0.75rem' }}>
                  ⚠️ Cash collection required
                </span>
              )}
            </div>
          )}
        </div>
      )}

      {/* Release Actions */}
      <div style={{
        padding: 'var(--space-3)',
        background: '#f8fafc',
        borderRadius: 'var(--radius-1)',
        border: '1px solid #e2e8f0'
      }}>
        <div style={{ marginBottom: 'var(--space-2)' }}>
          <textarea
            value={releaseNotes}
            onChange={(e) => setReleaseNotes(e.target.value)}
            placeholder="Release notes (optional)..."
            style={{
              width: '100%',
              minHeight: '50px',
              padding: 'var(--space-2)',
              border: '1px solid #d1d5db',
              borderRadius: 'var(--radius-1)',
              fontSize: '0.875rem',
              resize: 'vertical'
            }}
          />
        </div>
        
        <div className="cluster" style={{ gap: 'var(--space-2)' }}>
          <button
            onClick={() => handleRelease(false, false)}
            disabled={!commission.has_pod_photos || isReleasing}
            style={{
              background: commission.has_pod_photos && !isReleasing ? '#10b981' : '#9ca3af',
              color: 'white',
              border: 'none',
              padding: '0.375rem 0.75rem',
              borderRadius: 'var(--radius-1)',
              fontSize: '0.875rem',
              cursor: commission.has_pod_photos && !isReleasing ? 'pointer' : 'not-allowed',
              fontWeight: '500'
            }}
          >
            {isReleasing ? '🔄' : '🤖'} AI Release
          </button>
          
          {aiAnalysis?.ai_verification?.cash_collection_required && (
            <button
              onClick={() => onMarkCashCollected({ 
                tripId: commission.trip_id, 
                notes: releaseNotes || 'Cash collection confirmed' 
              })}
              disabled={isMarkingCash || isReleasing}
              style={{
                background: '#f59e0b',
                color: 'white',
                border: 'none',
                padding: '0.375rem 0.75rem',
                borderRadius: 'var(--radius-1)',
                fontSize: '0.875rem',
                cursor: isMarkingCash ? 'not-allowed' : 'pointer',
                fontWeight: '500'
              }}
            >
              {isMarkingCash ? '💰' : '💰'} Cash Collected
            </button>
          )}
          
          <button
            onClick={() => {
              const confirmed = window.confirm('Manual override bypasses AI verification. Continue?');
              if (confirmed) handleRelease(true, true);
            }}
            disabled={isReleasing || isMarkingCash}
            style={{
              background: '#6b7280',
              color: 'white',
              border: 'none',
              padding: '0.375rem 0.75rem',
              borderRadius: 'var(--radius-1)',
              fontSize: '0.875rem',
              cursor: isReleasing || isMarkingCash ? 'not-allowed' : 'pointer',
              fontWeight: '500'
            }}
          >
            ⚠️ Manual
          </button>
        </div>
      </div>
    </div>
  );
}

(DriverCommissionsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
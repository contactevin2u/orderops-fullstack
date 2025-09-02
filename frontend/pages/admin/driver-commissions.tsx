import React from 'react';
import AdminLayout from '@/components/admin/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { 
  listDrivers, 
  listDriverOrders, 
  markSuccess, 
  updateCommission, 
  listUpsellRecords, 
  releaseUpsellIncentive 
} from '@/utils/api';

export default function DriverCommissionsPage() {
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0, 7));
  const [activeTab, setActiveTab] = React.useState<'commissions' | 'upsells'>('commissions');
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
                <div style={{ display: 'flex', gap: 0 }}>
                  {[
                    { key: 'commissions', label: 'Delivery Commissions', count: orders.length },
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
                        fontSize: '0.875rem'
                      }}
                    >
                      {tab.label} ({tab.count})
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Commissions Tab */}
            {activeTab === 'commissions' && (
              <div className="card">
                <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
                  Delivery Commissions - {selectedDriver?.name || `Driver ${driverId}`} - {month}
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
                {orders.map((order: any) => (
                  <OrderCard 
                    key={order.id} 
                    order={order}
                    onRelease={() => releaseCommissionMutation.mutate(order.id)}
                    isReleasing={releaseCommissionMutation.isPending}
                    onUpdateCommission={(amount: number) => 
                      updateCommissionMutation.mutate({ orderId: order.id, amount })
                    }
                    isUpdatingCommission={updateCommissionMutation.isPending}
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
          background: '#eff6ff',
          borderRadius: 'var(--radius-2)',
          border: '1px solid #dbeafe'
        }}>
          <h3 style={{ fontWeight: 500, color: '#1e40af', marginBottom: 'var(--space-2)' }}>
            💡 Commission Process
          </h3>
          <div className="stack" style={{ fontSize: '0.875rem', color: '#1e40af' }}>
            <p><strong>1. Order must be DELIVERED</strong> status</p>
            <p><strong>2. Driver must have uploaded POD (Proof of Delivery) photo</strong></p>
            <p><strong>3. Click &quot;Release Commission&quot; to pay the driver</strong></p>
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
  isUpdatingCommission
}: { 
  order: any; 
  onRelease: () => void;
  isReleasing: boolean;
  onUpdateCommission: (amount: number) => void;
  isUpdatingCommission: boolean;
}) {
  const [showPodPhotos, setShowPodPhotos] = React.useState(false);
  const [commissionAmount, setCommissionAmount] = React.useState('');
  
  const trip = order.trip || {};
  const currentCommission = trip.commission?.computed_amount || order.commission || 0;
  const podPhotos = trip.pod_photo_urls || (trip.pod_photo_url ? [trip.pod_photo_url] : []);
  const hasPodPhoto = podPhotos.length > 0;
  const isDelivered = trip.status === 'DELIVERED'; // Check trip status, not order status
  const canRelease = isDelivered && hasPodPhoto && currentCommission > 0;
  
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
                fontSize: '0.875rem'
              }}
              disabled={isUpdatingCommission}
            />
            {isUpdatingCommission && <span style={{ fontSize: '0.75rem', color: '#6b7280' }}>Saving...</span>}
          </div>
        </div>

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
            borderRadius: 'var(--radius-2)',
            fontSize: '0.875rem',
            cursor: canRelease && !isReleasing ? 'pointer' : 'not-allowed',
            fontWeight: '500',
            minWidth: '120px'
          }}
        >
          {isReleasing ? 'Releasing...' : 'Release Commission'}
        </button>
      </div>

      {/* Status Indicators */}
      <div style={{ display: 'flex', gap: 'var(--space-3)', fontSize: '0.875rem' }}>
        <span style={{ color: isDelivered ? '#15803d' : '#6b7280' }}>
          {isDelivered ? '✅' : '⏳'} Delivered
        </span>
        <span style={{ color: hasPodPhoto ? '#15803d' : '#d97706' }}>
          {hasPodPhoto ? '✅' : '⚠️'} POD Photo
        </span>
        <span style={{ color: currentCommission > 0 ? '#15803d' : '#6b7280' }}>
          {currentCommission > 0 ? '✅' : '⏳'} Commission Set
        </span>
        {trip.commission?.actualized_at && (
          <span style={{ color: '#15803d' }}>
            ✅ Released
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

(DriverCommissionsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
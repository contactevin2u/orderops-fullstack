import React from 'react';
import Link from 'next/link';
import AdminLayout from '@/components/admin/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDrivers, listDriverOrders, markSuccess } from '@/utils/api';

export default function DriverCommissionsPage() {
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0, 7));
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

  const drivers = driversQuery.data || [];
  const orders = ordersQuery.data || [];
  const selectedDriver = drivers.find((d: any) => d.id == driverId);

  return (
    <div className="main">
      <div className="container">
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
            Driver Commissions
          </h1>
          <p style={{ opacity: 0.8 }}>
            Review deliveries and release driver commissions
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
          <div className="card">
            <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>
              Orders for {selectedDriver?.name || `Driver ${driverId}`} - {month}
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
                  />
                ))}
              </div>
            )}
          </div>
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

function OrderCard({ order, onRelease, isReleasing }: { 
  order: any; 
  onRelease: () => void;
  isReleasing: boolean;
}) {
  const [showPodPhotos, setShowPodPhotos] = React.useState(false);
  const trip = order.trip || {};
  const commission = trip.commission?.computed_amount || order.commission || 0;
  const podPhotos = trip.pod_photo_urls || (trip.pod_photo_url ? [trip.pod_photo_url] : []);
  const hasPodPhoto = podPhotos.length > 0;
  const isDelivered = order.status === 'DELIVERED';
  const canRelease = isDelivered && hasPodPhoto && commission > 0;

  return (
    <div style={{
      padding: 'var(--space-4)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-2)',
      background: 'var(--color-background)'
    }}>
      <div className="cluster" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h3 style={{ fontSize: '1rem', fontWeight: 600, marginBottom: 'var(--space-1)' }}>
            Order #{order.code || order.id}
          </h3>
          <div className="cluster" style={{ gap: 'var(--space-2)', fontSize: '0.875rem' }}>
            <span style={{ 
              padding: '0.125rem 0.5rem', 
              borderRadius: 'var(--radius-1)',
              background: isDelivered ? '#dcfce7' : '#fef3c7',
              color: isDelivered ? '#15803d' : '#d97706'
            }}>
              {order.status}
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
        
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontSize: '0.875rem', opacity: 0.7 }}>Commission</div>
          <div style={{ fontSize: '1.25rem', fontWeight: 600 }}>
            RM {commission}
          </div>
        </div>
      </div>

      <div style={{ marginTop: 'var(--space-4)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div className="cluster" style={{ gap: 'var(--space-4)', fontSize: '0.875rem' }}>
          <span style={{ color: isDelivered ? '#15803d' : '#6b7280' }}>
            {isDelivered ? '✅' : '⏳'} Delivered
          </span>
          <span style={{ color: hasPodPhoto ? '#15803d' : '#d97706' }}>
            {hasPodPhoto ? '✅' : '⚠️'} POD Photo
          </span>
          <span style={{ color: commission > 0 ? '#15803d' : '#6b7280' }}>
            {commission > 0 ? '✅' : '⏳'} Commission Set
          </span>
        </div>
        
        <div className="cluster" style={{ gap: 'var(--space-2)' }}>
          <Link href={`/orders/${order.id}`}>
            <button 
              className="btn"
              style={{
                background: '#f3f4f6',
                color: '#374151',
                border: '1px solid #d1d5db',
                padding: '0.5rem 1rem',
                borderRadius: 'var(--radius-2)',
                fontSize: '0.875rem',
                cursor: 'pointer'
              }}
            >
              Edit
            </button>
          </Link>
          
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
              fontWeight: '500'
            }}
          >
            {isReleasing ? 'Releasing...' : 'Release Commission'}
          </button>
        </div>
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

(DriverCommissionsPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;
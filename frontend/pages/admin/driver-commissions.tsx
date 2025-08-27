import React from 'react';
import Image from 'next/image';
import AdminLayout from '@/components/admin/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDrivers, listDriverOrders, addPayment, markSuccess, updateCommission } from '@/utils/api';
import StatusBadge from '@/components/StatusBadge';

export default function DriverCommissionsPage() {
  const qc = useQueryClient();
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0, 7)); // yyyy-mm

  const driversQuery = useQuery({
    queryKey: ['drivers'],
    queryFn: listDrivers,
  });
  const rowsQuery = useQuery({
    queryKey: ['driver-orders', driverId, month],
    queryFn: () => (driverId ? listDriverOrders(Number(driverId), month) : Promise.resolve([])),
    enabled: !!driverId,
  });
  const drivers = driversQuery.data || [];
  const rows = rowsQuery.data || [];

  const payAndSuccess = useMutation({
    mutationFn: async ({ orderId, amount, method, reference }: any) => {
      if (method && amount) {
        await addPayment({
          order_id: orderId,
          amount: Number(amount),
          method,
          reference,
          category: 'INITIAL',
          idempotencyKey: crypto.randomUUID(),
        });
      }
      await markSuccess(orderId);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] }),
  });

  const saveCommission = useMutation({
    mutationFn: async ({ orderId, amount }: any) => updateCommission(orderId, Number(amount)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['driver-orders', driverId, month] }),
  });

  return (
    <div>
      <h1 style={{ marginTop: 0 }}>Driver Commissions</h1>
      <div className="row" style={{ gap: 8, marginBottom: 12 }}>
        <label className="col">
          <span>Driver</span>
          <select
            className="select"
            value={driverId}
            onChange={(e) => setDriverId(e.target.value)}
          >
            <option value="">Select driver…</option>
            {drivers.map((d: any) => (
              <option key={d.id} value={d.id}>
                {d.name || `Driver ${d.id}`}
              </option>
            ))}
          </select>
        </label>
        <label className="col">
          <span>Month</span>
          <input
            className="input"
            type="month"
            value={month}
            onChange={(e) => setMonth(e.target.value)}
          />
        </label>
      </div>

      <div className="card">
        <table className="table">
          <thead>
            <tr>
              <th>Order</th>
              <th>Status</th>
              <th>POD</th>
              <th>Payment</th>
              <th>Commission</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {rowsQuery.isLoading && (
              <tr>
                <td colSpan={6} role="status">
                  Loading...
                </td>
              </tr>
            )}
            {rowsQuery.isError && (
              <tr>
                <td colSpan={6} role="alert">
                  Failed to load
                </td>
              </tr>
            )}
            {!rowsQuery.isLoading &&
              rows.map((o: any) => (
                <OrderRow
                  key={o.id}
                  o={o}
                  onPaySuccess={payAndSuccess.mutate}
                  onSaveCommission={saveCommission.mutate}
                />
              ))}
            {!rowsQuery.isLoading && rows.length === 0 && (
              <tr>
                <td colSpan={6} style={{ opacity: 0.7 }}>
                  No data
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <p aria-live="polite" style={{ marginTop: 8, fontSize: '0.875rem', opacity: 0.7 }}>
        {rows.length} orders loaded.
      </p>
    </div>
  );
}

function OrderRow({ o, onPaySuccess, onSaveCommission }: { o: any; onPaySuccess: any; onSaveCommission: any }) {
  const [method, setMethod] = React.useState('');
  const [amount, setAmount] = React.useState('');
  const [reference, setReference] = React.useState('');
  const [commission, setCommission] = React.useState(
    String(o?.trip?.commission?.computed_amount ?? o?.commission ?? '')
  );

  const apiBase = (process.env.NEXT_PUBLIC_API_URL || '').replace(/\/+$/, '');
  let pod = o?.trip?.pod_photo_url || o?.pod_photo_url;
  if (pod && !pod.startsWith('http')) pod = `${apiBase}${pod}`;
  const canSuccess =
    o.status === 'DELIVERED' &&
    !!pod &&
    ((method === '' && amount === '') || (!!method && !!amount));

  return (
    <tr>
      <td>{o.code || o.id}</td>
      <td><StatusBadge value={o.status} /></td>
      <td>
        {pod ? (
          <a href={pod} target="_blank" rel="noreferrer">
            <Image src={pod} alt="POD" width={64} height={64} />
          </a>
        ) : (
          <span style={{ opacity: 0.6 }}>No POD</span>
        )}
      </td>
      <td>
        <div style={{ display: 'flex', gap: 4 }}>
          <label className="sr-only" htmlFor={`method-${o.id}`}>
            Payment method
          </label>
          <select
            id={`method-${o.id}`}
            className="select"
            value={method}
            onChange={(e) => setMethod(e.target.value)}
          >
            <option value="">None</option>
            <option>Cash</option>
            <option>Online</option>
          </select>
          <label className="sr-only" htmlFor={`amount-${o.id}`}>
            Amount
          </label>
          <input
            id={`amount-${o.id}`}
            className="input"
            placeholder="Amount"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <label className="sr-only" htmlFor={`ref-${o.id}`}>
            Reference
          </label>
          <input
            id={`ref-${o.id}`}
            className="input"
            placeholder="Ref (optional)"
            value={reference}
            onChange={(e) => setReference(e.target.value)}
          />
        </div>
      </td>
      <td>
        <div style={{ display: 'flex', gap: 4 }}>
          <label className="sr-only" htmlFor={`commission-${o.id}`}>
            Commission
          </label>
          <input
            id={`commission-${o.id}`}
            className="input"
            placeholder="Commission"
            value={commission}
            onChange={(e) => setCommission(e.target.value)}
          />
          <button
            className="btn secondary"
            onClick={() => onSaveCommission({ orderId: o.id, amount: commission })}
          >
            Save
          </button>
        </div>
      </td>
      <td>
        <button
          className="btn"
          disabled={!canSuccess}
          title={!canSuccess ? 'Requires POD and valid payment (if provided)' : undefined}
          onClick={() => onPaySuccess({ orderId: o.id, amount, method, reference })}
        >
          Mark Success
        </button>
      </td>
    </tr>
  );
}

(DriverCommissionsPage as any).getLayout = (page:any) => <AdminLayout>{page}</AdminLayout>;

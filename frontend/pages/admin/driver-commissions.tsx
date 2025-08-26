import React from 'react';
import Image from 'next/image';
import AdminLayout from '@/components/admin/AdminLayout';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listDrivers, listDriverCommissions, addPayment, markSuccess, updateCommission } from '@/utils/api';
import StatusBadge from '@/components/StatusBadge';

export default function DriverCommissionsPage(){
  const qc = useQueryClient();
  const [driverId, setDriverId] = React.useState<string>('');
  const [month, setMonth] = React.useState<string>(new Date().toISOString().slice(0,7)); // yyyy-mm

  const { data: drivers } = useQuery({
    queryKey: ['drivers'],
    queryFn: listDrivers,
  });
  const { data: rows } = useQuery({
    queryKey: ['commissions', driverId, month],
    queryFn: () => (driverId ? listDriverCommissions(Number(driverId)) : Promise.resolve([])),
    enabled: !!driverId,
  });

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
    onSuccess: () => qc.invalidateQueries({ queryKey: ['commissions', driverId, month] }),
  });

  const saveCommission = useMutation({
    mutationFn: async ({ orderId, amount }: any) => updateCommission(orderId, Number(amount)),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['commissions', driverId, month] }),
  });

  return (
    <div>
      <h1 style={{marginTop:0}}>Driver Commissions</h1>
      <div className="row" style={{gap:8, marginBottom:12}}>
        <select className="select" value={driverId} onChange={e=>setDriverId(e.target.value)}>
          <option value="">Select driver…</option>
          {(drivers||[]).map((d:any)=> <option key={d.id} value={d.id}>{d.name||`Driver ${d.id}`}</option>)}
        </select>
        <input className="input" type="month" value={month} onChange={e=>setMonth(e.target.value)} />
      </div>

      <div className="card">
        <table className="table">
          <thead><tr><th>Order</th><th>Status</th><th>POD</th><th>Payment</th><th>Commission</th><th></th></tr></thead>
          <tbody>
            {(rows||[]).map((o:any)=>(
              <OrderRow key={o.id} o={o} onPaySuccess={payAndSuccess.mutate} onSaveCommission={saveCommission.mutate} />
            ))}
            {(!rows || rows.length===0) && <tr><td colSpan={6} style={{opacity:.7}}>No data</td></tr>}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function OrderRow({ o, onPaySuccess, onSaveCommission }:{ o:any; onPaySuccess:any; onSaveCommission:any }){
  const [method,setMethod] = React.useState('');
  const [amount,setAmount] = React.useState('');
  const [reference,setReference] = React.useState('');
  const [commission,setCommission] = React.useState(String(o?.trip?.commission?.computed_amount ?? o?.commission ?? ''));

  const pod = o?.trip?.pod_photo_url || o?.pod_photo_url;
  const canSuccess = o.status === 'DELIVERED' && (!!pod) && ((method==='' && amount==='') || (!!method && !!amount));

  return (
    <tr>
      <td>{o.code || o.id}</td>
      <td><StatusBadge value={o.status} /></td>
      <td>{pod ? <a href={pod} target="_blank" rel="noreferrer"><Image src={pod} alt="POD" width={64} height={64}/></a> : <span style={{opacity:.6}}>No POD</span>}</td>
      <td>
        <div style={{display:'flex',gap:4}}>
          <select className="select" value={method} onChange={e=>setMethod(e.target.value)}>
            <option value="">None</option>
            <option>Cash</option>
            <option>Online</option>
          </select>
          <input className="input" placeholder="Amount" value={amount} onChange={e=>setAmount(e.target.value)} />
          <input className="input" placeholder="Ref (optional)" value={reference} onChange={e=>setReference(e.target.value)} />
        </div>
      </td>
      <td>
        <div style={{display:'flex',gap:4}}>
          <input className="input" placeholder="Commission" value={commission} onChange={e=>setCommission(e.target.value)} />
          <button className="btn secondary" onClick={()=>onSaveCommission({ orderId: o.id, amount: commission })}>Save</button>
        </div>
      </td>
      <td>
        <button className="btn" disabled={!canSuccess} onClick={()=>onPaySuccess({ orderId: o.id, amount, method, reference })}>Mark Success</button>
      </td>
    </tr>
  );
}

(DriverCommissionsPage as any).getLayout = (page:any) => <AdminLayout>{page}</AdminLayout>;

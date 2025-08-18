import { useEffect, useState } from 'react'
import { api } from '../lib/api'

type Order = { id:number, code:string, type:string, status:string, subtotal:number, total:number, paid_amount:number, balance:number, customer_name:string }

export default function Ops() {
  const [orders, setOrders] = useState<Order[]>([])
  const [amount, setAmount] = useState('')
  const [orderId, setOrderId] = useState<number|undefined>(undefined)
  const [exportStart, setExportStart] = useState('2025-08-01')
  const [exportEnd, setExportEnd] = useState('2025-08-31')

  async function load() {
    const data = await api<Order[]>('/orders')
    setOrders(data)
  }
  useEffect(()=>{ load() }, [])

  async function addPayment() {
    if (!orderId) return
    await api('/payments', { method:'POST', body: JSON.stringify({ order_id: orderId, amount: parseFloat(amount) }) })
    setAmount(''); setOrderId(undefined); load()
  }

  async function voidPayment(id: number) {
    await api(`/payments/${id}/void`, { method:'POST', body: JSON.stringify({ reason: 'operator void' }) })
    load()
  }

  function downloadExport() {
    window.location.href = `${process.env.NEXT_PUBLIC_API_BASE}/export/cash.xlsx?start=${exportStart}&end=${exportEnd}`
  }

  return (
    <div className="container">
      <h1>Operations</h1>

      <div className="card">
        <h3>Export (Cash Basis)</h3>
        <div className="row">
          <label>Start:</label><input value={exportStart} onChange={e=>setExportStart(e.target.value)} />
          <label>End:</label><input value={exportEnd} onChange={e=>setExportEnd(e.target.value)} />
          <button onClick={downloadExport}>Download Excel</button>
        </div>
      </div>

      <div className="card">
        <h3>Record Payment</h3>
        <div className="row">
          <select value={orderId || ''} onChange={e=>setOrderId(parseInt(e.target.value))}>
            <option value="">Select Order</option>
            {orders.map(o=> <option key={o.id} value={o.id}>{o.code} - {o.customer_name}</option>)}
          </select>
          <input placeholder="Amount (RM)" value={amount} onChange={e=>setAmount(e.target.value)} />
          <button onClick={addPayment} disabled={!orderId || !amount}>Add Payment</button>
        </div>
      </div>

      <div className="card">
        <h3>Orders</h3>
        <table>
          <thead><tr><th>Code</th><th>Customer</th><th>Type</th><th>Status</th><th>Total</th><th>Paid</th><th>Balance</th><th>Docs</th></tr></thead>
          <tbody>
            {orders.map(o=> (
              <tr key={o.id}>
                <td>{o.code}</td>
                <td>{o.customer_name}</td>
                <td>{o.type}</td>
                <td>{o.status}</td>
                <td>RM {o.total.toFixed(2)}</td>
                <td>RM {o.paid_amount.toFixed(2)}</td>
                <td>RM {o.balance.toFixed(2)}</td>
                <td>
                  <a href={`${process.env.NEXT_PUBLIC_API_BASE}/documents/invoice/${o.id}.pdf`} target="_blank" rel="noreferrer">Invoice</a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}

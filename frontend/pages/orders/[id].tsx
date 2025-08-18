import { useRouter } from "next/router";
import { useEffect, useState } from "react";
import { getOrders, updateOrder, voidOrder, addPayment } from "../../lib/api";

export default function OrderDetailPage() {
  const router = useRouter();
  the: any) { setMsg(e.message || "Failed"); }
  }

  if (!order) return <div className="p-4">Loading...</div>;

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-bold">Order #{order.id} - {order.code}</h1>
      <div className="space-y-2">
        <div>Type: {order.type}</div>
        <div>Customer: {order.customer?.name} ({order.customer?.phone})</div>
        <div>Address: {order.customer?.address}</div>
        <div>Total: RM {order.total} | Paid: RM {order.paid_amount} | Balance: RM {order.balance}</div>
      </div>

      <div className="space-y-2 border p-3 rounded">
        <h3 className="font-semibold">Edit</h3>
        <textarea className="border p-2 w-full" placeholder="Notes" value={note} onChange={e => setNote(e.target.value)} />
        <select className="border p-2" value={status} onChange={e => setStatus(e.target.value)}>
          <option>NEW</option><option>ACTIVE</option><option>RETURNED</option><option>CANCELLED</option><option>COMPLETED</option>
        </select>
        <button className="px-3 py-2 bg-black text-white rounded" onClick={save}>Save</button>
      </div>

      <div className="space-y-2 border p-3 rounded">
        <h3 className="font-semibold">Record Payment</h3>
        <input className="border p-2 w-40" placeholder="Amount" value={payAmt} onChange={e => setPayAmt(e.target.value)} />
        <button className="px-3 py-2 bg-green-600 text-white rounded" onClick={record}>Add Payment</button>
      </div>

      <div className="space-y-2 border p-3 rounded">
        <h3 className="font-semibold">Void Order</h3>
        <input className="border p-2 w-full" placeholder="Reason (optional)" value={voidReason} onChange={e => setVoidReason(e.target.value)} />
        <button className="px-3 py-2 bg-red-600 text-white rounded" onClick={voidOrd}>Void Entire Order</button>
      </div>

      {msg && <div className="text-blue-700">{msg}</div>}
    </div>
  );
}

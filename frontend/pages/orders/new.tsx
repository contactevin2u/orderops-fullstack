import { useState } from "react";
import { createOrder } from "../../lib/api";

export default function NewOrderPage() {
  const [payload, setPayload] = useState<any>({
    customer: { name: "", phone: "", address: "" },
    order: {
      code: "",
      type: "OUTRIGHT",
      delivery_date: "",
      items: [{ name: "", qty: 1, unit_price: "0.00", item_type: "OUTRIGHT" }],
      charges: { delivery_fee: "0.00", discount: "0.00" }
    }
  });
  const [msg, setMsg] = useState<string>("");

  async function submit() {
    try {
      const res = await createOrder(payload);
      setMsg("Created order id " + res.id);
    } catch (e: any) {
      setMsg(e.message || "Failed");
    }
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-bold">New Order</h1>
      <div className="space-y-2">
        <input className="border p-2 w-full" placeholder="Order Code (optional)" value={payload.order.code || ""} onChange={e => setPayload({ ...payload, order: { ...payload.order, code: e.target.value } })} />
        <input className="border p-2 w-full" placeholder="Customer Name" value={payload.customer.name} onChange={e => setPayload({ ...payload, customer: { ...payload.customer, name: e.target.value } })} />
        <input className="border p-2 w-full" placeholder="Phone" value={payload.customer.phone} onChange={e => setPayload({ ...payload, customer: { ...payload.customer, phone: e.target.value } })} />
        <textarea className="border p-2 w-full" placeholder="Address" value={payload.customer.address} onChange={e => setPayload({ ...payload, customer: { ...payload.customer, address: e.target.value } })} />
        <select className="border p-2" value={payload.order.type} onChange={e => setPayload({ ...payload, order: { ...payload.order, type: e.target.value } })}>
          <option value="OUTRIGHT">OUTRIGHT</option>
          <option value="INSTALLMENT">INSTALLMENT</option>
          <option value="RENTAL">RENTAL</option>
        </select>
        <input className="border p-2" placeholder="Delivery YYYY-MM-DD" value={payload.order.delivery_date || ""} onChange={e => setPayload({ ...payload, order: { ...payload.order, delivery_date: e.target.value } })} />
        <div className="border p-2 space-y-2">
          <h3 className="font-semibold">Item</h3>
          <input className="border p-2 w-full" placeholder="Name" value={payload.order.items[0].name} onChange={e => setPayload({ ...payload, order: { ...payload.order, items: [{ ...payload.order.items[0], name: e.target.value }] } })} />
          <input className="border p-2 w-24" placeholder="Qty" value={payload.order.items[0].qty} onChange={e => setPayload({ ...payload, order: { ...payload.order, items: [{ ...payload.order.items[0], qty: Number(e.target.value) || 1 }] } })} />
          <input className="border p-2 w-40" placeholder="Unit Price" value={payload.order.items[0].unit_price} onChange={e => setPayload({ ...payload, order: { ...payload.order, items: [{ ...payload.order.items[0], unit_price: e.target.value }] } })} />
        </div>
        <button className="px-3 py-2 bg-black text-white rounded" onClick={submit}>Create</button>
        {msg && <div>{msg}</div>}
      </div>
    </div>
  );
}

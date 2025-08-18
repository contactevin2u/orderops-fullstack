import { useEffect, useState } from "react";
import { getOutstanding, addPayment } from "../lib/api";

export default function OutstandingPage() {
  const [data, setData] = useState<any>({ INSTALLMENT: [], RENTAL: [] });
  const [type, setType] = useState<string>("INSTALLMENT");
  const [paying, setPaying] = useState<{ [k: number]: string }>({});
  const [err, setErr] = useState<string>("");

  useEffect(() => {
    getOutstanding(type).then(setData).catch(e => setErr(e.message || "Failed"));
  }, [type]);

  const rows = (data[type] || []) as any[];

  async function submitPayment(orderId: number) {
    const amount = paying[orderId];
    if (!amount) return;
    try {
      await addPayment({ order_id: orderId, amount });
      const fresh = await getOutstanding(type);
      setData(fresh);
      setPaying(p => ({ ...p, [orderId]: "" }));
    } catch (e: any) {
      alert(e.message || "Failed to pay");
    }
  }

  return (
    <div className="p-4 space-y-4">
      <h1 className="text-2xl font-bold">Outstanding ({type})</h1>
      <div className="space-x-2">
        <button className={`px-3 py-1 rounded ${type === "INSTALLMENT" ? "bg-black text-white" : "bg-gray-200"}`} onClick={() => setType("INSTALLMENT")}>Installments</button>
        <button className={`px-3 py-1 rounded ${type === "RENTAL" ? "bg-black text-white" : "bg-gray-200"}`} onClick={() => setType("RENTAL")}>Rentals</button>
      </div>
      {err && <div className="text-red-600">{err}</div>}
      <div className="overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left border-b">
              <th className="p-2">Code</th>
              <th className="p-2">Customer</th>
              <th className="p-2">Months</th>
              <th className="p-2">Monthly</th>
              <th className="p-2">Paid</th>
              <th className="p-2">Balance</th>
              <th className="p-2">Pay</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r: any) => (
              <tr key={r.order_id} className="border-b">
                <td className="p-2">{r.code}</td>
                <td className="p-2">{r.customer}</td>
                <td className="p-2">{r.months_elapsed}</td>
                <td className="p-2">RM {r.monthly_amount}</td>
                <td className="p-2">RM {r.paid}</td>
                <td className="p-2 font-semibold">RM {r.balance_computed}</td>
                <td className="p-2">
                  <div className="flex gap-2">
                    <input className="border px-2 py-1 w-24" placeholder="Amount" value={paying[r.order_id] || ""} onChange={e => setPaying(p => ({ ...p, [r.order_id]: e.target.value }))} />
                    <button className="px-3 py-1 bg-green-600 text-white rounded" onClick={() => submitPayment(r.order_id)}>Pay</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

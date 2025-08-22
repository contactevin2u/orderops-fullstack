import Layout from "@/components/Layout";
import React from "react";
import { useRouter } from "next/router";
import { createManualOrder } from "@/utils/api";

interface ItemInput {
  name: string;
  item_type: string;
  qty: number;
  unit_price: string;
  monthly_amount: string;
}

export default function NewOrderPage(){
  const router = useRouter();
  const [custName,setCustName] = React.useState("");
  const [custPhone,setCustPhone] = React.useState("");
  const [custAddress,setCustAddress] = React.useState("");

  const [type,setType] = React.useState("OUTRIGHT");
  const [deliveryDate,setDeliveryDate] = React.useState("");
  const [notes,setNotes] = React.useState("");

  const [items,setItems] = React.useState<ItemInput[]>([{ name:"", item_type:"OUTRIGHT", qty:1, unit_price:"", monthly_amount:"" }]);

  const [busy,setBusy] = React.useState(false);
  const [err,setErr] = React.useState("");

  function updateItem(idx:number, field:string, value:unknown){
    const copy = [...items];
    copy[idx] = { ...copy[idx], [field]: value };
    setItems(copy);
  }

  function addItem(){
    setItems([...items, { name:"", item_type:"OUTRIGHT", qty:1, unit_price:"", monthly_amount:"" }]);
  }

  function removeItem(idx:number){
    setItems(items.filter((_,i)=>i!==idx));
  }

  async function onCreate(){
    setBusy(true); setErr("");
    try{
      const payload = {
        customer: { name: custName, phone: custPhone || undefined, address: custAddress || undefined },
        order: {
          type,
          delivery_date: deliveryDate || undefined,
          notes: notes || undefined,
          items: items.map(it=>({
            name: it.name,
            item_type: it.item_type,
            qty: Number(it.qty||0),
            unit_price: Number(it.unit_price||0),
            line_total: Number(it.unit_price||0) * Number(it.qty||0),
            ...(it.monthly_amount ? { monthly_amount: Number(it.monthly_amount||0) } : {})
          }))
        }
      };
      const out = await createManualOrder(payload);
      const oid = out?.id || out?.order_id;
      if(oid) router.push(`/orders/${oid}`);
    }catch(e){ const err = e as { message?: string }; setErr(err?.message || "Create failed"); }
    finally{ setBusy(false); }
  }

  return (
    <Layout>
      <div className="card">
        <h2 style={{marginTop:0}}>New Order</h2>
        <div className="row">
          <div className="col"><label>Customer Name</label><input className="input" value={custName} onChange={e=>setCustName(e.target.value)} /></div>
          <div className="col"><label>Phone</label><input className="input" value={custPhone} onChange={e=>setCustPhone(e.target.value)} /></div>
        </div>
        <div style={{marginTop:8}}><label>Address</label><textarea className="textarea" rows={2} value={custAddress} onChange={e=>setCustAddress(e.target.value)} /></div>
        <div className="row">
          <div className="col"><label>Type</label>
            <select className="select" value={type} onChange={e=>setType(e.target.value)}>
              <option>OUTRIGHT</option>
              <option>INSTALLMENT</option>
              <option>RENTAL</option>
              <option>MIXED</option>
            </select>
          </div>
          <div className="col"><label>Delivery Date</label><input className="input" type="date" value={deliveryDate} onChange={e=>setDeliveryDate(e.target.value)} /></div>
        </div>
        <div style={{marginTop:8}}><label>Notes</label><textarea className="textarea" rows={2} value={notes} onChange={e=>setNotes(e.target.value)} /></div>

        <div className="hr" />
        <h3>Items</h3>
        <table className="table">
          <thead><tr><th>Name</th><th>Type</th><th>Qty</th><th>Unit Price</th><th>Monthly</th><th></th></tr></thead>
          <tbody>
            {items.map((it,idx)=>(
              <tr key={idx}>
                <td><input className="input" value={it.name} onChange={e=>updateItem(idx,'name',e.target.value)} /></td>
                <td>
                  <select className="select" value={it.item_type} onChange={e=>updateItem(idx,'item_type',e.target.value)}>
                    <option>OUTRIGHT</option>
                    <option>INSTALLMENT</option>
                    <option>RENTAL</option>
                    <option>FEE</option>
                  </select>
                </td>
                <td><input className="input" value={it.qty} onChange={e=>updateItem(idx,'qty',e.target.value)} /></td>
                <td><input className="input" value={it.unit_price} onChange={e=>updateItem(idx,'unit_price',e.target.value)} /></td>
                <td><input className="input" value={it.monthly_amount} onChange={e=>updateItem(idx,'monthly_amount',e.target.value)} /></td>
                <td><button className="btn secondary" onClick={()=>removeItem(idx)}>Remove</button></td>
              </tr>
            ))}
            <tr><td colSpan={6}><button className="btn secondary" onClick={addItem}>Add Item</button></td></tr>
          </tbody>
        </table>

        {err && <div style={{marginTop:8,color:'#ffb3b3'}}>{err}</div>}
        <div style={{marginTop:8}}><button className="btn" onClick={onCreate} disabled={busy || !custName || items.length===0}>Create Order</button></div>
      </div>
    </Layout>
  );
}

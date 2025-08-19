import Layout from "@/components/Layout";
import React from "react";
import { parseMessage, createOrderFromParsed } from "@/utils/api";

export default function ParsePage(){
  const [text, setText] = React.useState("");
  const [parsed, setParsed] = React.useState<any>(null);
  const [err, setErr] = React.useState<string>("");
  const [busy, setBusy] = React.useState(false);
  const [msg, setMsg] = React.useState<string>("");

  async function onParse(){
    setBusy(true); setErr(""); setMsg("");
    try{
      const res = await parseMessage(text);
      setParsed(res);
    }catch(e:any){
      setErr(e?.message || "Parse failed");
    }finally{ setBusy(false); }
  }

  async function onCreate(){
    if(!parsed){ setErr("Nothing parsed."); return; }
    setBusy(true); setErr(""); setMsg("");
    try{
      const out = await createOrderFromParsed(parsed);
      setMsg("Order created: ID "+(out?.id || out?.order_id || JSON.stringify(out)));
    }catch(e:any){
      setErr(e?.message || "Create failed");
    }finally{ setBusy(false); }
  }

  return (
    <Layout>
      <div className="row">
        <div className="col">
          <div className="card">
            <h2 style={{marginTop:0}}>Paste Message</h2>
            <textarea className="textarea" rows={12} placeholder="Paste WhatsApp message here..." value={text} onChange={e=>setText(e.target.value)} />
            <div style={{display:"flex", gap:8, marginTop:8}}>
              <button className="btn" disabled={busy || !text.trim()} onClick={onParse}>Parse</button>
              <button className="btn secondary" disabled={busy || !parsed} onClick={onCreate}>Create Order</button>
            </div>
            {err && <div style={{marginTop:8,color:"#ffb3b3"}}>{err}</div>}
            {msg && <div style={{marginTop:8,color:"#9fffba"}}>{msg}</div>}
          </div>
        </div>
        <div className="col">
          <div className="card">
            <h2 style={{marginTop:0}}>Parsed JSON (editable)</h2>
            <textarea className="textarea" rows={12} value={parsed?JSON.stringify(parsed,null,2):""} onChange={e=>{
              try{ setParsed(JSON.parse(e.target.value)); setErr(""); }catch{ setErr("Invalid JSON"); }
            }} />
          </div>
        </div>
      </div>
    </Layout>
  );
}

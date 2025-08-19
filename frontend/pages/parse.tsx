import Layout from "@/components/Layout";
import { parseMessage, createOrderFromParsed } from "@/utils/api";
import { useState } from "react";
import OrderForm from "@/components/OrderForm";

export default function ParsePage() {
  const [text, setText] = useState("");
  const [parsed, setParsed] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [created, setCreated] = useState<any | null>(null);

  async function doParse() {
    setErr(null); setParsed(null); setCreated(null);
    try {
      const p = await parseMessage(text.trim());
      // Normalize plan field if missing
      if (p?.order && p.order.plan == null) p.order.plan = {};
      setParsed(p);
    } catch (e: any) {
      setErr(e.message || String(e));
    }
  }

  async function createDirect() {
    if (!parsed) return;
    setCreating(true); setErr(null); setCreated(null);
    try {
      try {
        const out = await createOrderFromParsed(parsed);
        setCreated(out);
      } catch {
        const out = await createOrderFromParsed({ parsed });
        setCreated(out);
      }
    } catch (e: any) {
      setErr(e.message || String(e));
    } finally {
      setCreating(false);
    }
  }

  return (
    <Layout>
      <h2 style={{marginTop:0}}>Parse & Create</h2>
      <textarea className="input" rows={10} placeholder="Paste customer message here..." value={text} onChange={e=>setText(e.target.value)} />
      <div style={{marginTop:8, display:'flex', gap:8}}>
        <button className="btn" onClick={doParse}>Parse</button>
        <button className="btn ok" onClick={createDirect} disabled={!parsed || creating}>{creating ? "Creating..." : "Create Immediately"}</button>
      </div>
      {err && <div style={{color:"var(--err)", marginTop:8}}>{err}</div>}

      {parsed && (
        <div style={{marginTop:16}}>
          <h3>Parsed (editable)</h3>
          <OrderForm parsed={parsed} onSaved={(o)=>setCreated(o)} />
        </div>
      )}

      {created && (
        <div className="card" style={{marginTop:16}}>
          <h3>Created!</h3>
          <pre className="code">{JSON.stringify(created, null, 2)}</pre>
        </div>
      )}
    </Layout>
  );
}

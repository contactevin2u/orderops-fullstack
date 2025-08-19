import Layout from "@/components/Layout";
import React from "react";
import { parseMessage, createOrderFromParsed } from "@/utils/api";

// Local helper so this page works even if utils/api wasn't updated yet.
function normalizeParsedForOrder(input: any) {
  if (!input) return null;
  const payload = typeof input === "object" && "parsed" in input ? input.parsed : input;
  const core = payload && payload.data ? payload.data : payload;

  if (core?.customer && core?.order) return { customer: core.customer, order: core.order };
  if (!core) return null;

  // If parse returned something odd, try a best-effort split
  if (!core.customer && (core.order || core.items)) {
    return { customer: core.customer || {}, order: core.order || core };
  }
  return core;
}

export default function ParsePage() {
  const [text, setText] = React.useState("");
  const [rawParsed, setRawParsed] = React.useState<any>(null);       // raw response from /parse
  const [editJson, setEditJson] = React.useState<string>("");        // editable normalized JSON text
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string>("");
  const [msg, setMsg] = React.useState<string>("");

  function setNormalizedEditor(obj: any) {
    const norm = normalizeParsedForOrder(obj) || {};
    const toPost = norm?.customer && norm?.order ? { customer: norm.customer, order: norm.order } : norm;
    setEditJson(JSON.stringify(toPost, null, 2));
  }

  async function onParse() {
    setBusy(true); setErr(""); setMsg("");
    try {
      const res = await parseMessage(text);
      setRawParsed(res);
      setNormalizedEditor(res);
    } catch (e: any) {
      setErr(e?.message || "Parse failed");
    } finally { setBusy(false); }
  }

  async function onCreate() {
    setBusy(true); setErr(""); setMsg("");
    try {
      // Use what's in the editor (so user can tweak)
      let payload: any = null;
      try {
        payload = JSON.parse(editJson);
      } catch {
        throw new Error("Edited JSON is not valid JSON.");
      }

      // Enforce the correct shape: { customer, order }
      const norm = normalizeParsedForOrder(payload) || payload;
      const toPost = norm?.customer && norm?.order ? { customer: norm.customer, order: norm.order } : null;
      if (!toPost) throw new Error("Payload must include { customer, order }.");

      const out = await createOrderFromParsed(toPost); // send only the top-level shape
      setMsg("Order created: ID " + (out?.id || out?.order_id || JSON.stringify(out)));
    } catch (e: any) {
      setErr(e?.message || "Create failed");
    } finally { setBusy(false); }
  }

  return (
    <Layout>
      <div className="row">
        <div className="col">
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Paste Message</h2>
            <textarea
              className="textarea"
              rows={12}
              placeholder="Paste WhatsApp message here..."
              value={text}
              onChange={(e) => setText(e.target.value)}
            />
            <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
              <button className="btn" disabled={busy || !text.trim()} onClick={onParse}>Parse</button>
              <button className="btn secondary" disabled={busy || !editJson.trim()} onClick={onCreate}>Create Order</button>
            </div>
            {err && <div style={{ marginTop: 8, color: "#ffb3b3" }}>{err}</div>}
            {msg && <div style={{ marginTop: 8, color: "#9fffba" }}>{msg}</div>}
          </div>

          {rawParsed && (
            <div className="card" style={{ marginTop: 12 }}>
              <h3 style={{ marginTop: 0 }}>Raw Parse Response (read-only)</h3>
              <pre className="textarea" style={{ whiteSpace: "pre-wrap" }}>
                {JSON.stringify(rawParsed, null, 2)}
              </pre>
            </div>
          )}
        </div>

        <div className="col">
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Payload To Be Posted (editable)</h2>
            <p style={{ marginTop: 0, opacity: 0.85 }}>
              This is the exact JSON the frontend will POST to <code>/orders</code>. It must be:
              <code>{` { "customer": {...}, "order": {...} }`}</code>.
            </p>
            <textarea
              className="textarea"
              rows={24}
              value={editJson}
              onChange={(e) => setEditJson(e.target.value)}
            />
          </div>
        </div>
      </div>
    </Layout>
  );
}

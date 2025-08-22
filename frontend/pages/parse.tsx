import Layout from "@/components/Layout";
import React from "react";
import { parseMessage, createOrderFromParsed, ParseResponse, Order } from "@/utils/api";

// Local helper so this page works even if utils/api wasn't updated yet.
function normalizeParsedForOrder(input: unknown) {
  if (!input) return null;
  const payload =
    typeof input === "object" && input !== null && "parsed" in input
      ? (input as { parsed: unknown }).parsed
      : input;
  const core =
    (typeof payload === "object" && payload !== null && "data" in payload
      ? (payload as { data: unknown }).data
      : payload);

  if (
    typeof core === "object" &&
    core !== null &&
    "customer" in core &&
    "order" in core
  )
    return {
      customer: (core as Record<string, unknown>)["customer"],
      order: (core as Record<string, unknown>)["order"],
    };
  if (!core) return null;

  const obj = core as Record<string, unknown>;
  if (!("customer" in obj) && ("order" in obj || "items" in obj)) {
    return { customer: (obj["customer"] as Record<string, unknown> | undefined) || {}, order: obj["order"] || obj };
  }
  return core;
}

export default function ParsePage() {
  const [text, setText] = React.useState("");
  const [rawParsed, setRawParsed] = React.useState<ParseResponse | null>(null); // raw response from /parse
  const [editJson, setEditJson] = React.useState<string>("");        // editable normalized JSON text
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState<string>("");
  const [msg, setMsg] = React.useState<string>("");

  function setNormalizedEditor(obj: unknown) {
    const norm = (normalizeParsedForOrder(obj) as Record<string, unknown> | null) || {};
    const toPost =
      norm && "customer" in norm && "order" in norm
        ? { customer: norm["customer"], order: norm["order"] }
        : norm;
    setEditJson(JSON.stringify(toPost, null, 2));
  }

  async function onParse() {
    setBusy(true); setErr(""); setMsg("");
    try {
      const res = await parseMessage(text);
      setRawParsed(res);
      setNormalizedEditor(res);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setErr(err?.message || "Parse failed");
    } finally { setBusy(false); }
  }

  async function onCreate() {
    setBusy(true); setErr(""); setMsg("");
    try {
      // Use what's in the editor (so user can tweak)
      let payload: unknown = null;
      try {
        payload = JSON.parse(editJson);
      } catch {
        throw new Error("Edited JSON is not valid JSON.");
      }

      // Enforce the correct shape: { customer, order }
        const norm = (normalizeParsedForOrder(payload) as Record<string, unknown> | null) || payload;
        const toPost =
          norm && typeof norm === "object" && "customer" in norm && "order" in norm
            ? { customer: norm["customer"], order: norm["order"] }
            : null;
      if (!toPost) throw new Error("Payload must include { customer, order }.");

      const out: Order = await createOrderFromParsed(toPost); // send only the top-level shape
      const oid =
        (out as { id?: number }).id ??
        (out as { order_id?: number }).order_id ??
        JSON.stringify(out);
      setMsg("Order created: ID " + oid);
    } catch (e: unknown) {
      const err = e as { message?: string };
      setErr(err?.message || "Create failed");
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

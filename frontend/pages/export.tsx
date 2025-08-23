import Layout from "@/components/Layout";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import React from "react";

export default function ExportPage() {
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const [mark, setMark] = React.useState(false);
  const base = process.env.NEXT_PUBLIC_API_URL || "/_api";

  function download(kind: "cash" | "payments_received") {
    if (!start || !end) return;
    const url = `${base}/export/${kind}.xlsx?start=${start}&end=${end}${
      mark ? "&mark=true" : ""
    }`;
    if (typeof window !== "undefined") {
      window.open(url, "_blank");
    }
  }

  return (
    <Layout>
      <div className="small-container stack">
        <Card>
          <h2 style={{ marginTop: 0, marginBottom: 16 }}>Export Payments</h2>
          <div className="stack" style={{ gap: 8 }}>
            <div>
              <label style={{ display: 'block', marginBottom: 4 }}>Start Date</label>
              <input
                className="input"
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: 4 }}>End Date</label>
              <input
                className="input"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
            <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <input
                type="checkbox"
                checked={mark}
                onChange={(e) => setMark(e.target.checked)}
              />
              Mark as exported
            </label>
            <div style={{ fontSize: '0.9em', opacity: 0.8 }}>
              Preview shows all payments; marking excludes already exported
              payments in future runs.
            </div>
            <div style={{ display: 'flex', gap: 8, paddingTop: 8 }}>
              <Button onClick={() => download('cash')} disabled={!start || !end}>
                Cash Export
              </Button>
              <Button
                variant="secondary"
                onClick={() => download('payments_received')}
                disabled={!start || !end}
              >
                Payments Received
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
}


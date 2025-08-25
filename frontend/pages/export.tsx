import Card from "@/components/Card";
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
    <div className="small-container stack">
      <Card className="stack">
        <h2>Export Payments</h2>
        <div className="stack">
          <label className="stack">
            <span>Start Date</span>
            <input
              className="input"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
            />
          </label>
          <label className="stack">
            <span>End Date</span>
            <input
              className="input"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
            />
          </label>
          <label className="cluster">
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
          <div className="cluster">
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
  );
}


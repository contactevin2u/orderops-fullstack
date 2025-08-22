import Layout from "@/components/Layout";
import Card from "@/components/ui/Card";
import Button from "@/components/ui/Button";
import React from "react";

export default function ExportPage() {
  const [start, setStart] = React.useState("");
  const [end, setEnd] = React.useState("");
  const base = process.env.NEXT_PUBLIC_API_URL || "/_api";

  function download(kind: "cash" | "payments_received") {
    if (!start || !end) return;
    const url = `${base}/export/${kind}.xlsx?start=${start}&end=${end}`;
    if (typeof window !== "undefined") {
      window.open(url, "_blank");
    }
  }

  return (
    <Layout>
      <div className="max-w-md mx-auto space-y-4">
        <Card>
          <h2 className="text-lg font-semibold mb-4">Export Payments</h2>
          <div className="space-y-2">
            <div>
              <label className="block mb-1">Start Date</label>
              <input
                className="input w-full"
                type="date"
                value={start}
                onChange={(e) => setStart(e.target.value)}
              />
            </div>
            <div>
              <label className="block mb-1">End Date</label>
              <input
                className="input w-full"
                type="date"
                value={end}
                onChange={(e) => setEnd(e.target.value)}
              />
            </div>
            <div className="flex gap-2 pt-2">
              <Button
                onClick={() => download("cash")}
                disabled={!start || !end}
              >
                Cash Export
              </Button>
              <Button
                variant="secondary"
                onClick={() => download("payments_received")}
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


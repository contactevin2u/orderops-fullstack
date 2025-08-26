import * as React from "react";
import clsx from "clsx";

const STYLES: Record<string, string> = {
  PENDING: "bg-yellow-100 text-yellow-800",
  ACTIVE: "bg-blue-100 text-blue-800",
  COMPLETED: "bg-green-100 text-green-800",
  RETURNED: "bg-gray-200 text-gray-800",
  CANCELLED: "bg-red-100 text-red-800",
};

export function StatusPill({ status }: { status: string }) {
  const style = STYLES[status] || "bg-gray-100 text-gray-800";
  return (
    <span className={clsx("inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium", style)}>
      {status}
    </span>
  );
}

export default StatusPill;

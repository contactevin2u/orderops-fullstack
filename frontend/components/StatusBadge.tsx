import React from "react";

export default function StatusBadge({ value }: { value?: string }){
  const txt = value || "UNKNOWN";
  return <span className="badge">{txt}</span>;
}

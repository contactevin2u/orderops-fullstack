import * as React from "react";

interface ToolbarProps {
  children: React.ReactNode;
}

export function Toolbar({ children }: ToolbarProps) {
  return (
    <div className="flex flex-wrap items-center justify-between gap-2">
      {children}
    </div>
  );
}

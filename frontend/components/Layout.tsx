import Link from "next/link";
import React from "react";

export default function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="container">
      <header style={{display:"flex",alignItems:"center",justifyContent:"space-between",margin:"12px 0"}}>
        <h1 style={{margin:0,fontSize:20}}>OrderOps</h1>
        <nav className="nav">
          <Link href="/">Dashboard</Link>
          <Link href="/parse">Parse & Create</Link>
          <Link href="/orders">Orders</Link>
          <Link href="/reports/outstanding">Outstanding</Link>
        </nav>
      </header>
      <main>{children}</main>
    </div>
  );
}

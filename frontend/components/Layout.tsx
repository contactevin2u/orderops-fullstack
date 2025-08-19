import Link from "next/link";
import { useRouter } from "next/router";
import { ReactNode } from "react";

const links = [
  { href: "/", label: "Dashboard" },
  { href: "/parse", label: "Parse & Create" },
  { href: "/orders", label: "Orders" },
  { href: "/reports/outstanding", label: "Outstanding" },
];

export default function Layout({ children }: { children: ReactNode }) {
  const r = useRouter();
  return (
    <div className="container">
      <h1 style={{margin:0}}>🧾 OrderOps</h1>
      <div className="nav">
        {links.map(l => (
          <Link key={l.href} href={l.href} className={r.pathname === l.href ? "active" : ""}>
            {l.label}
          </Link>
        ))}
      </div>
      <div className="card">
        {children}
      </div>
      <div style={{marginTop:12}}>
        <small>API: {process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}</small>
      </div>
    </div>
  );
}

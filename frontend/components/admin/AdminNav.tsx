import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

export default function AdminNav() {
  const { pathname } = useRouter();
  const items = [
    { href: '/admin', label: 'Dashboard' },
    { href: '/admin/drivers', label: 'Drivers' },
    { href: '/admin/routes', label: 'Routes' },
    { href: '/admin/assign', label: 'Assign Orders' },
    { href: '/admin/lorry-management', label: 'Lorry Management' },
    { href: '/admin/driver-commissions', label: 'Commissions' },
    { href: '/admin/users', label: 'Users' },
  ];
  return (
    <nav className="header-inner">
      <div className="nav">
        {items.map((item) => (
          <Link
            key={item.href}
            className={`nav-link ${pathname === item.href ? 'active' : ''}`}
            href={item.href}
            aria-current={pathname === item.href ? 'page' : undefined}
          >
            {item.label}
          </Link>
        ))}
      </div>
    </nav>
  );
}

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

export default function AdminNav() {
  const { pathname } = useRouter();
  const items = [
    { href: '/admin', label: 'Home' },
    { href: '/admin/routes', label: 'Routes' },
    { href: '/admin/assign', label: 'Assign' },
    { href: '/admin/driver-commissions', label: 'Driver Commissions' },
  ];
  return (
    <nav
      style={{
        display: 'flex',
        gap: 8,
        padding: 8,
        borderBottom: '1px solid #eee',
        background: '#fff',
        position: 'sticky',
        top: 0,
        zIndex: 10,
      }}
    >
      {items.map((item) => (
        <Link
          key={item.href}
          className="btn secondary"
          href={item.href}
          aria-current={pathname === item.href ? 'page' : undefined}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}

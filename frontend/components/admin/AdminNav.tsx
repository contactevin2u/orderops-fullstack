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
    { href: '/admin/driver-commissions', label: 'Commissions' },
    { href: '/admin/users', label: 'Users' },
  ];
  return (
    <nav className="container mx-auto px-4 py-3">
      <div className="flex flex-wrap gap-2">
        {items.map((item) => (
          <Link
            key={item.href}
            className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
              pathname === item.href
                ? 'bg-blue-100 text-blue-700 border border-blue-200'
                : 'text-gray-600 hover:text-gray-900 hover:bg-gray-100 border border-transparent'
            }`}
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

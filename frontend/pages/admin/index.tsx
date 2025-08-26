import Link from 'next/link';
import React from 'react';
import AdminLayout from '@/components/admin/AdminLayout';

export default function AdminIndexPage() {
  const items = [
    { href: '/admin/routes', label: 'Routes' },
    { href: '/admin/assign', label: 'Assign' },
    { href: '/admin/driver-commissions', label: 'Driver Commissions' },
  ];
  return (
    <div>
      <h1>Admin</h1>
      <ul style={{ display: 'flex', flexDirection: 'column', gap: 8, padding: 0 }}>
        {items.map((item) => (
          <li key={item.href} style={{ listStyle: 'none' }}>
            <Link className="btn" href={item.href}>
              {item.label}
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

(AdminIndexPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

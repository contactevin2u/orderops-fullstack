import Link from 'next/link';
import React from 'react';
import AdminLayout from '@/components/admin/AdminLayout';

export default function AdminIndexPage() {
  const sections = [
    {
      title: 'Driver Management',
      description: 'Manage drivers and their assignments',
      items: [
        { href: '/admin/drivers', label: 'Drivers', description: 'Create and manage driver accounts' },
        { href: '/admin/routes', label: 'Routes', description: 'Plan and manage delivery routes' },
        { href: '/admin/driver-commissions', label: 'Commissions', description: 'View driver commission reports' },
      ]
    },
    {
      title: 'Order Management', 
      description: 'Handle order assignments and tracking',
      items: [
        { href: '/admin/ai-assignments', label: 'AI Assignments', description: 'AI-powered order assignment and message parsing' },
        { href: '/admin/assign', label: 'Assign Orders', description: 'Assign orders to routes and drivers' },
      ]
    },
    {
      title: 'System Administration',
      description: 'Manage users and system settings',
      items: [
        { href: '/admin/users', label: 'Users', description: 'Create admin and cashier accounts' },
      ]
    }
  ];

  return (
    <div className="max-w-6xl">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">Admin Dashboard</h1>
        <p className="text-gray-600">Welcome to the OrderOps administration panel. Manage your drivers, routes, and system settings.</p>
      </div>

      <div className="space-y-8">
        {sections.map((section) => (
          <div key={section.title} className="bg-white rounded-lg border p-6">
            <div className="mb-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-2">{section.title}</h2>
              <p className="text-gray-600">{section.description}</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {section.items.map((item) => (
                <Link
                  key={item.href}
                  href={item.href}
                  className="block p-4 border border-gray-200 rounded-md hover:border-blue-300 hover:bg-blue-50 transition-colors group"
                >
                  <h3 className="font-medium text-gray-900 group-hover:text-blue-700 mb-1">
                    {item.label}
                  </h3>
                  <p className="text-sm text-gray-600">{item.description}</p>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-8 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 rounded-lg border border-blue-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-2">🚀 Quick Start Guide</h2>
        <div className="space-y-2 text-sm text-gray-700">
          <p><strong>1.</strong> Create driver accounts in the Drivers section</p>
          <p><strong>2.</strong> Set up delivery routes for your drivers</p>
          <p><strong>3.</strong> Assign orders to routes for efficient delivery</p>
          <p><strong>4.</strong> Monitor driver performance through commissions</p>
        </div>
      </div>
    </div>
  );
}

(AdminIndexPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

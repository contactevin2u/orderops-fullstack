import Link from 'next/link';
import React from 'react';
import { 
  Truck, 
  Map, 
  DollarSign, 
  Users,
  Calendar,
  ArrowRight,
  BarChart3,
  Settings,
  Package
} from 'lucide-react';
import AdminLayout from '@/components/Layout/AdminLayout';

export default function AdminIndexPage() {

  const modules = [
    {
      title: 'Driver Management',
      description: 'Create and manage driver accounts',
      href: '/admin/drivers',
      icon: Truck
    },
    {
      title: 'Route Planning', 
      description: 'Create and manage delivery routes',
      href: '/admin/routes',
      icon: Map
    },
    {
      title: 'Driver Commissions',
      description: 'Track driver earnings and performance',
      href: '/admin/driver-commissions',
      icon: DollarSign
    },
    {
      title: 'User Management',
      description: 'Manage admin and cashier accounts', 
      href: '/admin/users',
      icon: Users
    },
    {
      title: 'Inventory Management',
      description: 'Manage UID tracking and stock levels',
      href: '/admin/inventory',
      icon: Package
    }
  ];

  return (
    <div className="main">
      <div className="container">
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)' }}>
            OrderOps Admin
          </h1>
          <p style={{ opacity: 0.8 }}>
            Manage your delivery operations efficiently
          </p>
        </div>

        <div className="grid" style={{ 
          gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', 
          gap: 'var(--space-6)' 
        }}>
          {modules.map((module, index) => {
            const Icon = module.icon;
            return (
              <Link key={index} href={module.href} className="card" style={{ textDecoration: 'none' }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'flex-start', 
                  gap: 'var(--space-4)' 
                }}>
                  <div style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    width: '3rem',
                    height: '3rem',
                    borderRadius: 'var(--radius-2)',
                    background: 'var(--color-border)',
                    color: 'var(--color-text-muted)'
                  }}>
                    <Icon size={20} />
                  </div>
                  <div style={{ flex: 1 }}>
                    <h3 style={{ 
                      fontSize: '1.125rem', 
                      fontWeight: 600, 
                      marginBottom: 'var(--space-1)',
                      color: 'var(--color-text)'
                    }}>
                      {module.title}
                    </h3>
                    <p style={{ 
                      fontSize: '0.875rem',
                      color: 'var(--color-text-muted)',
                      margin: 0
                    }}>
                      {module.description}
                    </p>
                  </div>
                  <ArrowRight size={16} style={{ color: 'var(--color-text-muted)' }} />
                </div>
              </Link>
            );
          })}
        </div>
      </div>
    </div>
  );
}

(AdminIndexPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

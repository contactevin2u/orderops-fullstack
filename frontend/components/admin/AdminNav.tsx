import React, { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/router';

interface NavGroup {
  label: string;
  items: NavItem[];
}

interface NavItem {
  href: string;
  label: string;
  icon?: string;
}

export default function AdminNav() {
  const { pathname } = useRouter();
  const [openDropdown, setOpenDropdown] = useState<string | null>(null);

  const navGroups: NavGroup[] = [
    {
      label: 'Operations',
      items: [
        { href: '/admin', label: '📊 Dashboard', icon: '📊' },
        { href: '/admin/assign', label: '📋 Assign Orders', icon: '📋' },
        { href: '/admin/routes', label: '🗺️ Route Planning', icon: '🗺️' },
      ]
    },
    {
      label: 'Inventory & Stock',
      items: [
        { href: '/admin/uid-management', label: '🔍 UID Tracker', icon: '🔍' },
        { href: '/admin/bulk-uid-generator', label: '🏭 Bulk UID Generator', icon: '🏭' },
        { href: '/admin/stock-variance', label: '📈 Stock Variance', icon: '📈' },
        { href: '/admin/lorry-management', label: '🚛 Lorry Stock', icon: '🚛' },
        { href: '/admin/sku-management', label: '📦 SKU Management', icon: '📦' },
      ]
    },
    {
      label: 'Drivers & Fleet',
      items: [
        { href: '/admin/drivers', label: '👥 Driver Management', icon: '👥' },
        { href: '/admin/holds', label: '🚫 Driver Holds', icon: '🚫' },
        { href: '/admin/driver-stock', label: '📱 Driver Stock', icon: '📱' },
        { href: '/admin/driver-commissions', label: '💰 Commissions', icon: '💰' },
        { href: '/admin/driver-schedule', label: '📅 Schedule', icon: '📅' },
      ]
    },
    {
      label: 'System',
      items: [
        { href: '/admin/users', label: '👤 User Management', icon: '👤' },
        { href: '/admin/uid-generator', label: '🏷️ UID Generator', icon: '🏷️' },
      ]
    }
  ];

  const toggleDropdown = (groupLabel: string) => {
    setOpenDropdown(openDropdown === groupLabel ? null : groupLabel);
  };

  const isActiveGroup = (group: NavGroup) => {
    return group.items.some(item => pathname === item.href);
  };

  const getActiveItem = () => {
    for (const group of navGroups) {
      const activeItem = group.items.find(item => pathname === item.href);
      if (activeItem) return activeItem;
    }
    return null;
  };

  return (
    <nav className="header-inner">
      <div className="nav">
        {navGroups.map((group) => (
          <div key={group.label} className="nav-group nav-group-dropdown">
            <button
              className={`nav-link nav-group-button ${isActiveGroup(group) ? 'active' : ''}`}
              onClick={() => toggleDropdown(group.label)}
              onBlur={(e) => {
                // Close dropdown when clicking outside
                if (!e.currentTarget.parentElement?.contains(e.relatedTarget)) {
                  setTimeout(() => setOpenDropdown(null), 150);
                }
              }}
            >
              <span className="nav-group-label">{group.label}</span>
              <span style={{ marginLeft: '4px' }}>
                {getActiveItem()?.label || group.items[0]?.label}
              </span>
              <span style={{ marginLeft: '6px', fontSize: '0.75rem' }}>
                {openDropdown === group.label ? '▲' : '▼'}
              </span>
            </button>
            
            {openDropdown === group.label && (
              <div className="nav-dropdown-menu">
                {group.items.map((item) => (
                  <Link
                    key={item.href}
                    className={`nav-link ${pathname === item.href ? 'active' : ''}`}
                    href={item.href}
                    onClick={() => setOpenDropdown(null)}
                    aria-current={pathname === item.href ? 'page' : undefined}
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            )}
          </div>
        ))}
        
        <div className="nav-separator" />
        
        {/* Quick access to most used features */}
        <div className="nav-group">
          <Link
            className={`nav-link ${pathname === '/orders' ? 'active' : ''}`}
            href="/orders"
            aria-current={pathname === '/orders' ? 'page' : undefined}
          >
            🛒 Orders
          </Link>
          <Link
            className={`nav-link ${pathname === '/reports/outstanding' ? 'active' : ''}`}
            href="/reports/outstanding"
            aria-current={pathname === '/reports/outstanding' ? 'page' : undefined}
          >
            📄 Reports
          </Link>
        </div>
      </div>
    </nav>
  );
}

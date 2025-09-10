import Link from 'next/link';
import React from 'react';
import LanguageSwitcher from '../LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import {
  Inbox,
  ClipboardList,
  FileDown,
  BarChart2,
  CircleDollarSign,
  FilePlus,
  Wrench,
  Menu,
  Shield,
  Calendar,
  FileText,
  Smartphone,
  Truck,
  ChevronDown,
  Users,
  Route,
  UserCheck,
  Settings,
} from 'lucide-react';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { getMe } from '@/lib/api';

export type NavItem = {
  href: string;
  label: string;
  Icon: any;
  requiresAuth?: boolean;
};

export type NavGroup = {
  title: string;
  items: NavItem[];
};

export const navGroups: NavGroup[] = [
  {
    title: 'Core Operations',
    items: [
      { href: '/', label: 'nav.intake', Icon: Inbox },
      { href: '/orders', label: 'nav.orders', Icon: ClipboardList },
      { href: '/orders/new', label: 'orders.create', Icon: FilePlus },
      { href: '/quotations/new', label: 'New Quotation', Icon: FileText },
    ]
  },
  {
    title: 'Financial Operations',
    items: [
      { href: '/cashier', label: 'nav.cashier', Icon: CircleDollarSign },
      { href: '/adjustments', label: 'nav.adjustments', Icon: Wrench },
      { href: '/export', label: 'nav.export', Icon: FileDown },
      { href: '/reports/outstanding', label: 'nav.reports', Icon: BarChart2 },
    ]
  },
  {
    title: 'Operations Management',
    items: [
      { href: '/admin/driver-schedule', label: 'Driver Schedule', Icon: Calendar, requiresAuth: true },
      { href: '/admin/lorry-management', label: 'Lorry Management', Icon: Truck, requiresAuth: true },
      { href: '/admin/assign', label: 'Assign Orders', Icon: UserCheck, requiresAuth: true },
      { href: '/admin/routes', label: 'Routes', Icon: Route, requiresAuth: true },
    ]
  },
  {
    title: 'Monitoring & Control',
    items: [
      { href: '/admin/uid-management', label: 'UID Tracker', Icon: BarChart2, requiresAuth: true },
      { href: '/admin/holds', label: 'Driver Holds', Icon: Shield, requiresAuth: true },
      { href: '/admin/driver-commissions', label: 'Driver Commissions', Icon: CircleDollarSign, requiresAuth: true },
      { href: '/admin/drivers', label: 'Driver Management', Icon: Users, requiresAuth: true },
    ]
  },
  {
    title: 'System Settings',
    items: [
      { href: '/admin', label: 'Admin Dashboard', Icon: Settings, requiresAuth: true },
      { href: '/admin/users', label: 'User Management', Icon: Users, requiresAuth: true },
    ]
  }
];

// Legacy flat array for compatibility
export const navItems: NavItem[] = navGroups.flatMap(group => group.items);

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const [openDropdowns, setOpenDropdowns] = React.useState<Set<string>>(new Set());
  const menuRef = React.useRef<HTMLElement>(null);
  const headerRef = React.useRef<HTMLElement>(null);
  const { data: user, error: userErr } = useSWR('me', getMe, {
    shouldRetryOnError: false,
    errorRetryCount: 0,
    revalidateOnFocus: false,
    revalidateOnReconnect: false,
  });

  const pathname = React.useMemo(
    () => router.asPath.split('?')[0],
    [router.asPath]
  );

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const toggleDropdown = (groupTitle: string) => {
    setOpenDropdowns(prev => {
      const newSet = new Set(prev);
      if (newSet.has(groupTitle)) {
        newSet.delete(groupTitle);
      } else {
        newSet.add(groupTitle);
      }
      return newSet;
    });
  };

  const isGroupActive = (group: NavGroup) => {
    return group.items.some(item => isActive(item.href));
  };

  // Remove unused legacy filtering logic - now using navGroups directly
  React.useEffect(() => {
    if (mobileOpen) {
      const first = menuRef.current?.querySelector<HTMLElement>('a,button');
      first?.focus();
    }
  }, [mobileOpen]);
  React.useEffect(() => {
    const el = headerRef.current;
    if (!el) return;
    const update = () =>
      document.documentElement.style.setProperty(
        '--app-header-h',
        `${el.offsetHeight}px`
      );
    update();
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, []);
  
  // Handle authentication redirects
  React.useEffect(() => {
    if (userErr && (userErr as any).status === 401) {
      // Only redirect if we're not already on login/register page
      if (!pathname.startsWith('/login') && !pathname.startsWith('/register')) {
        router.replace('/login');
      }
    }
  }, [userErr, pathname, router]);
  React.useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (e.key === 'Escape') {
        setMobileOpen(false);
        setOpenDropdowns(new Set());
      }
      if (!mobileOpen) return;
      if (e.key === 'Tab') {
        const items = menuRef.current?.querySelectorAll<HTMLElement>('a,button');
        if (!items || items.length === 0) return;
        const first = items[0];
        const last = items[items.length - 1];
        if (!e.shiftKey && document.activeElement === last) {
          e.preventDefault();
          first.focus();
        } else if (e.shiftKey && document.activeElement === first) {
          e.preventDefault();
          last.focus();
        }
      }
    }
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [mobileOpen]);

  // Close dropdowns when clicking outside
  React.useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (!menuRef.current?.contains(e.target as Node)) {
        setOpenDropdowns(new Set());
      }
    }
    document.addEventListener('click', handleClickOutside);
    return () => document.removeEventListener('click', handleClickOutside);
  }, []);
  return (
    <div className="layout">
      <header ref={headerRef} className="header">
        <div className="header-inner">
          <h1>OrderOps</h1>
          <div className="header-actions">
            <Link 
              href="/mobile/delivery-status" 
              className="mobile-status-btn"
              title="Mobile Status"
            >
              <Smartphone style={{ width: 16, height: 16 }} />
            </Link>
            <button
              type="button"
              className="nav-link nav-toggle"
              aria-expanded={mobileOpen}
              aria-controls="primary-nav"
              onClick={() => setMobileOpen((o) => !o)}
            >
              <Menu style={{ width: 20, height: 20 }} />
              <span className="sr-only">{t('nav.menu')}</span>
            </button>
          </div>
          <nav
            id="primary-nav"
            ref={menuRef}
            className={`nav ${mobileOpen ? 'open' : ''}`}
            aria-label="Primary"
          >
            {navGroups.map((group, groupIndex) => {
              const groupItems = group.items.filter(item => !item.requiresAuth || !!user);
              if (groupItems.length === 0) return null;
              
              const isDropdownOpen = openDropdowns.has(group.title);
              const hasActiveItem = isGroupActive(group);
              
              return (
                <div key={group.title} className="nav-group">
                  {groupIndex > 0 && <div className="nav-separator" />}
                  <div className="nav-group-dropdown">
                    <button
                      className={`nav-link nav-group-button ${hasActiveItem ? 'active' : ''}`}
                      onClick={() => toggleDropdown(group.title)}
                      aria-expanded={isDropdownOpen}
                    >
                      <span>{group.title}</span>
                      <ChevronDown 
                        style={{ 
                          width: 16, 
                          height: 16, 
                          transform: isDropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
                          transition: 'transform 0.2s ease'
                        }} 
                      />
                    </button>
                    {isDropdownOpen && (
                      <div className="nav-dropdown-menu">
                        {groupItems.map(({ href, label, Icon }) => (
                          <Link
                            key={href}
                            href={href}
                            className={`nav-link ${isActive(href) ? 'active' : ''}`}
                            onClick={() => {
                              setMobileOpen(false);
                              setOpenDropdowns(new Set());
                            }}
                            title={t(label)}
                          >
                            <Icon style={{ width: 18, height: 18 }} />
                            <span>{t(label)}</span>
                          </Link>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
            <div className="nav-separator" />
            <LanguageSwitcher />
            {user ? (
              <>
                <span className="nav-link">{user.username}</span>
                <button
                  className="nav-link"
                  onClick={async () => {
                    await fetch('/_api/auth/logout', {
                      method: 'POST',
                      credentials: 'include',
                    });
                    router.replace('/login');
                  }}
                >
                  {t('nav.signout', { defaultValue: 'Sign out' })}
                </button>
              </>
            ) : userErr && (userErr as any).status === 401 ? (
              <Link className="nav-link" href="/login">
                {t('nav.signin', { defaultValue: 'Sign in' })}
              </Link>
            ) : null}
          </nav>
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
    </div>
  );
}

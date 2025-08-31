import Link from 'next/link';
import React from 'react';
import LanguageSwitcher from './LanguageSwitcher';
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
} from 'lucide-react';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { getMe } from '@/utils/api';

export type NavItem = {
  href: string;
  label: string;
  Icon: any;
  requiresAuth?: boolean;
};

export const navItems: NavItem[] = [
  { href: '/', label: 'nav.intake', Icon: Inbox },
  { href: '/orders', label: 'nav.orders', Icon: ClipboardList },
  { href: '/orders/new', label: 'orders.create', Icon: FilePlus },
  { href: '/export', label: 'nav.export', Icon: FileDown },
  { href: '/reports/outstanding', label: 'nav.reports', Icon: BarChart2 },
  { href: '/cashier', label: 'nav.cashier', Icon: CircleDollarSign },
  { href: '/adjustments', label: 'nav.adjustments', Icon: Wrench },
  { href: '/admin/driver-schedule', label: 'Driver Schedule', Icon: Calendar, requiresAuth: true },
  { href: '/admin', label: 'nav.admin', Icon: Shield, requiresAuth: true },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLElement>(null);
  const headerRef = React.useRef<HTMLElement>(null);
  const { data: user, error: userErr } = useSWR('me', getMe, {
    shouldRetryOnError: false,
  });

  const pathname = React.useMemo(
    () => router.asPath.split('?')[0],
    [router.asPath]
  );

  const isActive = (href: string) => {
    if (href === '/') return pathname === '/';
    return pathname === href || pathname.startsWith(`${href}/`);
  };

  const uniqueByHref = (items: NavItem[]) =>
    Array.from(new Map(items.map((i) => [i.href, i])).values());

  const items = uniqueByHref(navItems).filter(
    (i) => !i.requiresAuth || !!user
  );
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
  React.useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if (!mobileOpen) return;
      if (e.key === 'Escape') setMobileOpen(false);
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
  return (
    <div className="layout">
      <header ref={headerRef} className="header">
        <div className="header-inner">
          <h1>OrderOps</h1>
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
          <nav
            id="primary-nav"
            ref={menuRef}
            className={`nav ${mobileOpen ? 'open' : ''}`}
            aria-label="Primary"
          >
            {items.map(({ href, label, Icon }) => (
              <Link
                key={href}
                href={href}
                className={`nav-link ${isActive(href) ? 'active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                <Icon style={{ width: 20, height: 20 }} />
                <span>{t(label)}</span>
              </Link>
            ))}
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

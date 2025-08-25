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
  Wrench,
  Menu,
} from 'lucide-react';
import { useRouter } from 'next/router';
import { useSession, signIn, signOut } from 'next-auth/react';

export type NavItem = { href: string; label: string; Icon: any };
export const navItems: NavItem[] = [
  { href: '/', label: 'nav.intake', Icon: Inbox },
  { href: '/orders', label: 'nav.orders', Icon: ClipboardList },
  { href: '/export', label: 'nav.export', Icon: FileDown },
  { href: '/reports/outstanding', label: 'nav.reports', Icon: BarChart2 },
  { href: '/cashier', label: 'nav.cashier', Icon: CircleDollarSign },
  { href: '/adjustments', label: 'nav.adjustments', Icon: Wrench },
];

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const router = useRouter();
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const menuRef = React.useRef<HTMLDivElement>(null);
  const { data: session } = useSession();
  const pathname = router.asPath;
  const isActive = (href: string) => (href === '/' ? pathname === '/' : pathname.startsWith(href));
  React.useEffect(() => {
    if (mobileOpen) {
      const first = menuRef.current?.querySelector<HTMLElement>('a,button');
      first?.focus();
    }
  }, [mobileOpen]);
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
      <header className="header">
        <div className="header-inner">
          <h1>OrderOps</h1>
          <button
            className="nav-link nav-toggle"
            aria-expanded={mobileOpen}
            aria-controls="primary-nav"
            onClick={() => setMobileOpen((o) => !o)}
          >
            <Menu style={{ width: 20, height: 20 }} />
            <span className="sr-only">{t('nav.menu')}</span>
          </button>
          <nav id="primary-nav" ref={menuRef} className={`nav ${mobileOpen ? 'open' : ''}`}>
            {navItems.map(({ href, label, Icon }) => (
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
            {session ? (
              <button className="nav-link" onClick={() => signOut()}>
                {t('nav.signout', { defaultValue: 'Sign out' })}
              </button>
            ) : (
              <button className="nav-link" onClick={() => signIn('github')}>
                {t('nav.signin', { defaultValue: 'Sign in' })}
              </button>
            )}
          </nav>
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
    </div>
  );
}

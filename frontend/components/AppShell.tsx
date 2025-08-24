import React from 'react';
import Link from 'next/link';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import { Inbox, ClipboardList, FileDown, BarChart2, Menu } from 'lucide-react';
import { useRouter } from 'next/router';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const [user, setUser] = React.useState<any>(null);
  const [mobileOpen, setMobileOpen] = React.useState(false);
  const router = useRouter();
  const menuRef = React.useRef<HTMLDivElement>(null);

  React.useEffect(() => {
    fetch('/_api/auth/me', { credentials: 'include' })
      .then((r) => (r.ok ? r.json() : Promise.reject()))
      .then(setUser)
      .catch(() => {
        window.location.href = '/login';
      });
  }, []);

  function onLogout() {
    fetch('/_api/auth/logout', { method: 'POST', credentials: 'include' }).finally(() => {
      window.location.href = '/login';
    });
  }

  const nav = [
    { href: '/', label: t('nav.intake'), Icon: Inbox, roles: ['ADMIN', 'CASHIER'] },
    { href: '/orders', label: t('nav.orders'), Icon: ClipboardList, roles: ['ADMIN', 'CASHIER'] },
    { href: '/export', label: t('nav.export'), Icon: FileDown, roles: ['ADMIN'] },
    { href: '/reports/outstanding', label: t('nav.reports'), Icon: BarChart2, roles: ['ADMIN'] },
  ];

  const visible = nav.filter((n) => !n.roles || n.roles.includes(user?.role));

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

  if (!user) return null;

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
            {visible.map(({ href, label, Icon }) => (
              <Link
                key={href}
                href={href}
                className={`nav-link ${router.asPath.startsWith(href) ? 'active' : ''}`}
                onClick={() => setMobileOpen(false)}
              >
                <Icon style={{ width: 20, height: 20 }} />
                <span>{label}</span>
              </Link>
            ))}
            <LanguageSwitcher />
            <button onClick={onLogout} className="nav-link">
              {t('logout')}
            </button>
          </nav>
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
    </div>
  );
}

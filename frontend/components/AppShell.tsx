import React from 'react';
import Link from 'next/link';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import { Inbox, ClipboardList, FileDown, BarChart2 } from 'lucide-react';

export default function AppShell({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const [user, setUser] = React.useState<any>(null);

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

  if (!user) return null;

  return (
    <div className="layout">
      <header className="header">
        <div className="header-inner">
          <h1>OrderOps</h1>
          <nav className="nav">
            {visible.map(({ href, label, Icon }) => (
              <Link key={href} href={href} className="nav-link">
                <Icon style={{ width: 20, height: 20 }} />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <LanguageSwitcher />
          <button onClick={onLogout} className="nav-link">
            {t('logout')}
          </button>
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
    </div>
  );
}

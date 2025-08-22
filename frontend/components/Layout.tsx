import Link from 'next/link';
import React from 'react';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import { Inbox, Workflow } from 'lucide-react';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const nav = [
    { href: '/', label: t('nav.intake'), Icon: Inbox },
    { href: '/ops', label: t('nav.ops'), Icon: Workflow },
  ];
  return (
    <div className="layout">
      <header className="header">
        <div className="header-inner">
          <h1>OrderOps</h1>
          <nav className="nav">
            {nav.map(({ href, label, Icon }) => (
              <Link key={href} href={href} className="nav-link">
                <Icon style={{ width: 20, height: 20 }} />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <LanguageSwitcher />
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
    </div>
  );
}

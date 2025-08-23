import Link from 'next/link';
import React from 'react';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';
import {
  Inbox,
  Workflow,
  ClipboardList,
  FileInput,
  FileDown,
  BarChart2,
  CircleDollarSign,
  Wrench,
} from 'lucide-react';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  const nav = [
    { href: '/', label: t('nav.intake'), Icon: Inbox },
    { href: '/ops', label: t('nav.ops'), Icon: Workflow },
    { href: '/orders', label: t('nav.orders'), Icon: ClipboardList },
    { href: '/parse', label: t('nav.parse'), Icon: FileInput },
    { href: '/export', label: t('nav.export'), Icon: FileDown },
    { href: '/reports/outstanding', label: t('nav.reports'), Icon: BarChart2 },
    { href: '/cashier', label: t('nav.cashier'), Icon: CircleDollarSign },
    { href: '/adjustments', label: t('nav.adjustments'), Icon: Wrench },
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

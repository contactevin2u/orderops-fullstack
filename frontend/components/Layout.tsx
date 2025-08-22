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
    <div className="flex min-h-screen flex-col">
      <header className="sticky top-0 z-10 bg-gradient-to-r from-brand-500 to-accent-500 text-white shadow-md">
        <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
          <h1 className="text-xl font-semibold">OrderOps</h1>
          <nav className="flex items-center gap-6">
            {nav.map(({ href, label, Icon }) => (
              <Link
                key={href}
                href={href}
                className="flex items-center gap-1 text-sm font-medium transition-colors hover:text-white/80"
              >
                <Icon className="h-5 w-5" />
                <span>{label}</span>
              </Link>
            ))}
          </nav>
          <LanguageSwitcher />
        </div>
      </header>
      <main className="flex-1 bg-gradient-to-br from-brand-50 to-white p-6">
        <div className="mx-auto max-w-5xl">{children}</div>
      </main>
    </div>
  );
}

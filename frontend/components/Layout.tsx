import Link from 'next/link';
import React from 'react';
import LanguageSwitcher from './LanguageSwitcher';
import { useTranslation } from 'react-i18next';

export default function Layout({ children }: { children: React.ReactNode }) {
  const { t } = useTranslation();
  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-brand-500 text-white px-4 py-3 flex items-center justify-between gap-4">
        <h1 className="text-xl font-semibold">OrderOps</h1>
        <nav className="flex gap-4">
          <Link href="/" className="hover:underline">
            {t('nav.intake')}
          </Link>
          <Link href="/ops" className="hover:underline">
            {t('nav.ops')}
          </Link>
        </nav>
        <LanguageSwitcher />
      </header>
      <main className="flex-1 p-4 bg-brand-50">{children}</main>
    </div>
  );
}

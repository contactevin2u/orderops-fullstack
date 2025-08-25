import React from 'react';
import { useTranslation } from 'react-i18next';
import NotificationBell from './components/NotificationBell';
import DriverSWManager from './DriverSWManager';

type AppShellProps = {
  children: React.ReactNode;
  assignmentsCount: number;
  unread: number;
};

export default function AppShell({ children, assignmentsCount, unread }: AppShellProps) {
  const { t } = useTranslation();
  const today = new Date().toLocaleDateString(undefined, {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  });
  return (
    <div className="layout">
      <header className="header" style={{ background: '#1f2937' }}>
        <div className="header-inner">
          <div>{today}</div>
          <div className="cluster">
            <span>{t('driver.assignments.title')}</span>
            <span aria-label={t('driver.assignments.title')} className="badge">
              {assignmentsCount}
            </span>
            <NotificationBell count={unread} />
          </div>
        </div>
      </header>
      <main className="main">
        <div className="container">{children}</div>
      </main>
      <DriverSWManager />
    </div>
  );
}

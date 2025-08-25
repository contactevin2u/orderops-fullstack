import React from 'react';
import { useTranslation } from 'react-i18next';
import AppShell from '@/driver/AppShell';
import AssignmentCard from '@/driver/components/AssignmentCard';
import useAssignments from '@/driver/hooks/useAssignments';
import { usePushNotifications } from '@/driver/hooks/usePushNotifications';

export default function DriverHome() {
  const { t } = useTranslation();
  const [filter, setFilter] = React.useState<'today' | 'tomorrow' | 'all'>('today');

  const date = React.useMemo(() => {
    if (filter === 'today') return new Date().toISOString().slice(0, 10);
    if (filter === 'tomorrow') {
      const d = new Date();
      d.setDate(d.getDate() + 1);
      return d.toISOString().slice(0, 10);
    }
    return undefined;
  }, [filter]);

  const { data } = useAssignments(date);
  const assignments = data || [];

  const { permission, enablePush } = usePushNotifications();

  return (
    <AppShell assignmentsCount={assignments.length} unread={0}>
      {permission !== 'granted' && (
        <button className="btn" onClick={enablePush}>
          {t('driver.enableNotifications')}
        </button>
      )}
      <div className="cluster" style={{ marginBottom: 16 }}>
        <button className="btn secondary" onClick={() => setFilter('today')}>
          {t('driver.assignments.today')}
        </button>
        <button className="btn secondary" onClick={() => setFilter('tomorrow')}>
          {t('driver.assignments.tomorrow')}
        </button>
        <button className="btn secondary" onClick={() => setFilter('all')}>
          {t('driver.assignments.all')}
        </button>
      </div>
      {assignments.length === 0 && <p>{t('driver.assignments.none')}</p>}
      {assignments.map((a: any) => (
        <AssignmentCard
          key={a.id}
          assignment={a}
          onDetails={(id) => (window.location.href = `/driver/assignment/${id}`)}
        />
      ))}
    </AppShell>
  );
}

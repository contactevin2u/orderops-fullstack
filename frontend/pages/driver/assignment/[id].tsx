import React from 'react';
import { useRouter } from 'next/router';
import useSWR from 'swr';
import { useTranslation } from 'react-i18next';
import AppShell from '@/driver/AppShell';
import CallButton from '@/driver/components/CallButton';
import StatusStepper from '@/driver/components/StatusStepper';
import { fetchAssignmentDetail, updateAssignmentStatus } from '@/utils/api';

export default function AssignmentDetailPage() {
  const { t } = useTranslation();
  const router = useRouter();
  const id = router.query.id as string;

  const { data, mutate } = useSWR(id ? ['assignment', id] : null, () => fetchAssignmentDetail(id));
  const assignment = data as any;

  async function onChange(next: string, reason?: string) {
    await updateAssignmentStatus(id, next, reason);
    mutate();
  }

  if (!assignment) return null;

  return (
    <AppShell assignmentsCount={0} unread={0}>
      <h1>{assignment.order_code}</h1>
      {assignment.phone && <CallButton phone={assignment.phone} />}
      <p>{assignment.customer_name}</p>
      <p>{assignment.address}</p>
      <StatusStepper status={assignment.status} onChange={onChange} />
    </AppShell>
  );
}

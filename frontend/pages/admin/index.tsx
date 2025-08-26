import { useRouter } from 'next/router';
import React from 'react';

export default function AdminIndex() {
  const router = useRouter();
  React.useEffect(() => {
    const today = new Date().toISOString().slice(0, 10);
    router.replace({ pathname: '/admin/routes', query: { date: today } });
  }, [router]);
  return null;
}

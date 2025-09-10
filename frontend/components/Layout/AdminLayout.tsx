import React from 'react';
import { useRouter } from 'next/router';
import { useToast } from '@/hooks/useToast';
import { ToastContainer } from '@/components/ui/toast';
import AppLayout from './AppLayout';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const { toasts, removeToast } = useToast();

  return (
    <AppLayout>
      <div className="admin-content">
        {children}
      </div>
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </AppLayout>
  );
}

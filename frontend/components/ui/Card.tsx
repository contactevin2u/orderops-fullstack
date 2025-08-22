import React from 'react';
import clsx from 'clsx';

export default function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return <div className={clsx('bg-white rounded-xl shadow-sm p-4', className)}>{children}</div>;
}

import React from 'react';
import clsx from 'clsx';

export default function Card({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div className={clsx('rounded-2xl bg-white/70 p-6 shadow-lg backdrop-blur', className)}>{children}</div>
  );
}

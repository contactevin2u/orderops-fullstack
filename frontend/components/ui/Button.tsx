import clsx from 'clsx';
import React from 'react';

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary';
};

export default function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  const base =
    'inline-flex items-center justify-center rounded-xl px-4 py-2 font-semibold transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2';
  const styles =
    variant === 'secondary'
      ? 'bg-white/80 text-ink-900 shadow-sm hover:bg-white focus:ring-ink-400'
      : 'bg-gradient-to-r from-brand-500 to-accent-500 text-white shadow-md hover:from-brand-600 hover:to-accent-600 focus:ring-brand-500';
  return <button className={clsx(base, styles, className)} {...props} />;
}

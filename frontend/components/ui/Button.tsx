import clsx from 'clsx';
import React from 'react';

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary';
};

export default function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  const base = 'px-4 py-2 rounded-lg font-medium focus:outline-none focus:ring-2 focus:ring-offset-2';
  const styles =
    variant === 'secondary'
      ? 'bg-ink-200 text-ink-900 hover:bg-ink-400 focus:ring-ink-400'
      : 'bg-brand-500 text-white hover:bg-brand-600 focus:ring-brand-500';
  return <button className={clsx(base, styles, className)} {...props} />;
}

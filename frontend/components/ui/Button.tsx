import clsx from 'clsx';
import React from 'react';

export type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary';
};

export default function Button({ variant = 'primary', className, ...props }: ButtonProps) {
  return <button className={clsx('btn', variant === 'secondary' && 'secondary', className)} {...props} />;
}

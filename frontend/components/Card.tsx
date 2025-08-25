import React from 'react';
import clsx from 'clsx';

type Props = React.HTMLAttributes<HTMLDivElement> & {
  children: React.ReactNode;
};

export default function Card({ children, className, ...rest }: Props) {
  return (
    <div className={clsx('card', className)} {...rest}>
      {children}
    </div>
  );
}

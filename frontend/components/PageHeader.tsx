import React from 'react';
import clsx from 'clsx';

interface Props {
  title: React.ReactNode;
  subtitle?: React.ReactNode;
  actions?: React.ReactNode;
  className?: string;
}

export default function PageHeader({ title, subtitle, actions, className }: Props) {
  return (
    <div className={clsx('stack', className)}>
      <div className="cluster" style={{ justifyContent: 'space-between' }}>
        <div className="stack">
          <h1>{title}</h1>
          {subtitle && <p>{subtitle}</p>}
        </div>
        {actions && <div className="cluster">{actions}</div>}
      </div>
    </div>
  );
}

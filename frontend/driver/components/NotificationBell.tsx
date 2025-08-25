import React from 'react';

type Props = {
  count: number;
};

export default function NotificationBell({ count }: Props) {
  return (
    <button className="btn secondary" aria-label="notifications">
      <span role="img" aria-hidden>🔔</span>
      {count > 0 && <span style={{ marginLeft: 4 }}>{count}</span>}
    </button>
  );
}

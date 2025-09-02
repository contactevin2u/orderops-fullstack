import React from 'react';

export default function StatusBadge({ value }: { value?: string }) {
  const txt = value || "UNKNOWN";
  
  const getStatusClass = (status: string) => {
    switch (status.toUpperCase()) {
      case 'NEW':
      case 'PENDING':
        return 'badge badge-info';
      case 'ACTIVE':
      case 'ASSIGNED':
        return 'badge badge-warning';
      case 'COMPLETED':
      case 'DELIVERED':
      case 'SUCCESS':
        return 'badge badge-success';
      case 'CANCELLED':
      case 'VOID':
      case 'RETURNED':
        return 'badge badge-error';
      case 'ON_HOLD':
      case 'PAUSED':
        return 'badge badge-muted';
      default:
        return 'badge';
    }
  };
  
  return <span className={getStatusClass(txt)}>{txt}</span>;
}

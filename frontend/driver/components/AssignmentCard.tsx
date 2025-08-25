import React from 'react';
import { useTranslation } from 'react-i18next';
import CallButton from './CallButton';

type Assignment = {
  id: number | string;
  seq?: number;
  order_code?: string;
  customer_name?: string;
  phone?: string;
  cod?: number;
  map_url?: string;
};

type Props = {
  assignment: Assignment;
  onDetails: (id: number | string) => void;
};

export default function AssignmentCard({ assignment, onDetails }: Props) {
  const { t } = useTranslation();
  const maskedPhone = assignment.phone
    ? assignment.phone.replace(/(\d{3})\d{4}(\d+)/, '$1-XXXX-$2')
    : '';
  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div className="cluster" style={{ justifyContent: 'space-between' }}>
        <strong>{assignment.seq}</strong>
        <span>{assignment.order_code}</span>
      </div>
      <div>{assignment.customer_name}</div>
      <div>{maskedPhone}</div>
      {assignment.cod ? <div>RM {assignment.cod}</div> : null}
      <div className="cluster" style={{ marginTop: 8 }}>
        {assignment.phone && <CallButton phone={assignment.phone} />}
        {assignment.phone && (
          <button
            className="btn secondary"
            onClick={() => window.open(`https://wa.me/${assignment.phone}`)}
          >
            {t('driver.whatsapp')}
          </button>
        )}
        {assignment.map_url && (
          <button
            className="btn secondary"
            onClick={() => window.open(assignment.map_url, '_blank')}
          >
            {t('driver.map')}
          </button>
        )}
        <button
          className="btn secondary"
          onClick={() => onDetails(assignment.id)}
        >
          {t('driver.details')}
        </button>
      </div>
    </div>
  );
}

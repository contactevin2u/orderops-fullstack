import React from 'react';
import { useTranslation } from 'react-i18next';

type Props = {
  status: string;
  onChange: (next: string, reason?: string) => void;
};

export default function StatusStepper({ status, onChange }: Props) {
  const { t } = useTranslation();

  function start() {
    onChange('OUT_FOR_DELIVERY');
  }
  function delivered() {
    onChange('DELIVERED');
  }
  function failed() {
    const reason = window.prompt('Reason?') || '';
    onChange('FAILED', reason);
  }

  return (
    <div className="cluster" style={{ marginTop: 16 }}>
      {status === 'SCHEDULED' && (
        <button className="btn" onClick={start}>
          {t('driver.start')}
        </button>
      )}
      {status === 'OUT_FOR_DELIVERY' && (
        <>
          <button className="btn" onClick={delivered}>
            {t('driver.delivered')}
          </button>
          <button className="btn secondary" onClick={failed}>
            {t('driver.failed')}
          </button>
        </>
      )}
    </div>
  );
}

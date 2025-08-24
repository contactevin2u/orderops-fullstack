import React from 'react';
import { useTranslation } from 'react-i18next';

interface Props {
  open: boolean;
  onClose: () => void;
  onAccept: () => void;
  user?: string;
  ip?: string;
}

export default function TermsModal({ open, onClose, onAccept, user, ip }: Props) {
  const { t } = useTranslation();
  const [checked, setChecked] = React.useState(false);

  function handleAccept() {
    if (!checked) return;
    try {
      const entry = { ts: Date.now(), ...(user ? { user } : {}), ...(ip ? { ip } : {}) };
      const arr = JSON.parse(localStorage.getItem('terms-consent') || '[]');
      arr.push(entry);
      localStorage.setItem('terms-consent', JSON.stringify(arr));
    } catch {}
    onAccept();
    setChecked(false);
  }

  if (!open) return null;
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true">
      <div className="modal">
        <h2>{t('terms.title')}</h2>
        <div style={{ fontSize: '0.875rem', lineHeight: 1.4 }}>
          <p>{t('terms.payment')}</p>
          <p>{t('terms.ownership')}</p>
          <p>{t('terms.default')}</p>
          <p>{t('terms.ctos')}</p>
          <p>{t('terms.pdpa')}</p>
          <p>{t('terms.returns')}</p>
          <p>{t('terms.warranty')}</p>
          <p>{t('terms.governing')}</p>
          <p>{t('terms.entire')}</p>
        </div>
        <div style={{ marginTop: 16 }}>
          <label style={{ display: 'flex', gap: 8 }}>
            <input
              type="checkbox"
              checked={checked}
              onChange={(e) => setChecked(e.target.checked)}
            />
            {t('terms.agree')}
          </label>
        </div>
        <div style={{ marginTop: 16, display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
          <button className="btn secondary" onClick={onClose}>
            {t('cancel')}
          </button>
          <button className="btn" onClick={handleAccept} disabled={!checked}>
            {t('accept')}
          </button>
        </div>
        <div style={{ marginTop: 8 }}>
          <button className="nav-link" onClick={() => window.print()}>
            {t('terms.download')}
          </button>
          <p style={{ fontSize: '0.75rem', marginTop: 8 }}>
            {t('terms.disclaimer')}
          </p>
        </div>
      </div>
    </div>
  );
}

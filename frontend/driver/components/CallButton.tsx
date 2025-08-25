import React from 'react';
import { useTranslation } from 'react-i18next';

type Props = {
  phone: string;
};

function canDial() {
  if (typeof navigator === 'undefined') return false;
  return /Mobi|Android/i.test(navigator.userAgent);
}

export default function CallButton({ phone }: Props) {
  const { t } = useTranslation();
  const [copied, setCopied] = React.useState(false);
  const dialable = canDial();

  function call() {
    window.location.href = `tel:${phone}`;
  }

  async function copy() {
    try {
      await navigator.clipboard.writeText(phone);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (e) {
      // ignore
    }
  }

  if (dialable) {
    return (
      <button className="btn" onClick={call}>
        {t('driver.call')}
      </button>
    );
  }
  return (
    <div className="cluster">
      <span>{phone}</span>
      <button className="btn secondary" onClick={copy}>
        {copied ? t('driver.copied') : t('driver.call')}
      </button>
    </div>
  );
}

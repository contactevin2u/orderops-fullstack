import React from 'react';
import Card from '@/components/Card';
import Button from '@/components/ui/button';
import TermsModal from '@/components/ui/TermsModal';
import { useTranslation } from 'react-i18next';
import { parseMessage, createOrderFromParsed } from '@/utils/api';

function normalizeParsedForOrder(input: any) {
  if (!input) return null;
  const payload = typeof input === 'object' && 'parsed' in input ? input.parsed : input;
  const core = payload && payload.data ? payload.data : payload;

  if (core?.customer && core?.order) return { customer: core.customer, order: core.order };
  if (!core) return null;
  if (!core.customer && (core.order || core.items)) {
    return { customer: core.customer || {}, order: core.order || core };
  }
  return core;
}

export default function IntakePage() {
  const { t } = useTranslation();
  const [text, setText] = React.useState('');
  const [parsed, setParsed] = React.useState<any>(null);
  const [busy, setBusy] = React.useState(false);
  const [err, setErr] = React.useState('');
  const [msg, setMsg] = React.useState('');
  const [termsOpen, setTermsOpen] = React.useState(false);
  const [accepted, setAccepted] = React.useState(false);

  async function onParse() {
    setBusy(true); setErr(''); setMsg('');
    try {
      const res = await parseMessage(text);
      setParsed(res);
      setMsg('Parsed successfully');
    } catch (e: any) {
      setErr(e?.message || 'Parse failed');
    } finally {
      setBusy(false);
    }
  }

  async function createOrder() {
    setBusy(true); setErr(''); setMsg('');
    try {
      const out = await createOrderFromParsed(parsed);
      setMsg('Order created: ID ' + (out?.id || out?.order_id || JSON.stringify(out)));
    } catch (e: any) {
      setErr(e?.message || 'Create failed');
    } finally {
      setBusy(false);
    }
  }

  async function onCreate() {
    if (!accepted) {
      setTermsOpen(true);
      return;
    }
    await createOrder();
  }

  const toPost = normalizeParsedForOrder(parsed);

  return (
    <div className="stack" style={{ maxWidth: '48rem', margin: '0 auto' }}>
      <Card className="stack">
        <details>
          <summary>{t('help.intake.title')}</summary>
          <p>{t('help.intake.body')}</p>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{t('help.intake.sample')}</pre>
        </details>
        <textarea
          className="textarea"
          rows={10}
          placeholder={t('intake.placeholder')}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
        <div className="cluster" style={{ justifyContent: 'flex-end' }}>
          <Button disabled={busy || !text} onClick={onParse}>{t('intake.parse')}</Button>
          <Button variant="secondary" disabled={busy || !toPost} onClick={onCreate}>{t('intake.create')}</Button>
        </div>
        {err && <p style={{ fontSize: '0.875rem', color: '#ff4d4f' }}>{err}</p>}
        {msg && <p style={{ fontSize: '0.875rem', color: '#16a34a' }}>{msg}</p>}
      </Card>
      {toPost && (
        <Card className="stack">
          <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{JSON.stringify(toPost, null, 2)}</pre>
        </Card>
      )}
      <TermsModal
        open={termsOpen}
        onClose={() => setTermsOpen(false)}
        onAccept={() => {
          setAccepted(true);
          setTermsOpen(false);
          createOrder();
        }}
      />
    </div>
  );
}

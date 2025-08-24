import React from 'react';
import AppShell from '@/components/AppShell';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useTranslation } from 'react-i18next';
import { parseMessage } from '@/utils/api';

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

  async function onCreate() {
    setBusy(true); setErr(''); setMsg('');
    try {
      const out = await parseMessage(text, true);
      setParsed(out);
      const info = out?.created;
      setMsg('Order created: ID ' + (info?.order_id || info?.code || JSON.stringify(info)));
    } catch (e: any) {
      setErr(e?.message || 'Create failed');
    } finally {
      setBusy(false);
    }
  }

  const toPost = normalizeParsedForOrder(parsed);

  return (
    <AppShell>
      <div className="stack container" style={{ maxWidth: '48rem' }}>
        <Card>
          <textarea
            className="textarea"
            rows={10}
            placeholder={t('intake.placeholder')}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="row" style={{ justifyContent: 'flex-end' }}>
            <Button disabled={busy || !text} onClick={onParse}>{t('intake.parse')}</Button>
            <Button variant="secondary" disabled={busy || !text} onClick={onCreate}>{t('intake.create')}</Button>
          </div>
          {err && <p style={{ marginTop: 8, fontSize: '0.875rem', color: '#ff4d4f' }}>{err}</p>}
          {msg && <p style={{ marginTop: 8, fontSize: '0.875rem', color: '#16a34a' }}>{msg}</p>}
        </Card>
        {toPost && (
          <Card>
            <pre style={{ whiteSpace: 'pre-wrap', fontSize: '0.875rem' }}>{JSON.stringify(toPost, null, 2)}</pre>
          </Card>
        )}
      </div>
    </AppShell>
  );
}

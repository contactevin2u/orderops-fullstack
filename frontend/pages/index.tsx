import React from 'react';
import Layout from '@/components/Layout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
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
      const out = await createOrderFromParsed(parsed);
      setMsg('Order created: ID ' + (out?.id || out?.order_id || JSON.stringify(out)));
    } catch (e: any) {
      setErr(e?.message || 'Create failed');
    } finally {
      setBusy(false);
    }
  }

  const toPost = normalizeParsedForOrder(parsed);

  return (
    <Layout>
      <div className="max-w-3xl mx-auto space-y-4">
        <Card>
          <textarea
            className="w-full h-40 p-3 border border-ink-200 rounded-xl"
            placeholder={t('intake.placeholder')}
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="mt-4 flex justify-end gap-2">
            <Button disabled={busy || !text} onClick={onParse}>{t('intake.parse')}</Button>
            <Button variant="secondary" disabled={busy || !toPost} onClick={onCreate}>{t('intake.create')}</Button>
          </div>
          {err && <p className="mt-2 text-danger-500 text-sm">{err}</p>}
          {msg && <p className="mt-2 text-success-500 text-sm">{msg}</p>}
        </Card>
        {toPost && (
          <Card className="text-sm">
            <pre className="whitespace-pre-wrap">{JSON.stringify(toPost, null, 2)}</pre>
          </Card>
        )}
      </div>
    </Layout>
  );
}

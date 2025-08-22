import React from 'react';
import Layout from '@/components/Layout';
import Card from '@/components/ui/Card';
import Button from '@/components/ui/Button';
import { useTranslation } from 'react-i18next';

export default function IntakePage() {
  const { t } = useTranslation();
  const [text, setText] = React.useState('');
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
            <Button disabled={!text}>{t('intake.parse')}</Button>
            <Button variant="secondary">{t('intake.create')}</Button>
          </div>
        </Card>
      </div>
    </Layout>
  );
}

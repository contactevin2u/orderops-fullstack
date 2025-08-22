import Layout from '@/components/Layout';
import Card from '@/components/ui/Card';
import React from 'react';
import { useTranslation } from 'react-i18next';

export default function OpsPage() {
  const { t } = useTranslation();
  return (
    <Layout>
      <div className="max-w-4xl mx-auto space-y-4">
        <Card>
          <h2 className="text-lg font-semibold mb-4">{t('nav.ops')}</h2>
          <p className="text-ink-600">Coming soon.</p>
        </Card>
      </div>
    </Layout>
  );
}

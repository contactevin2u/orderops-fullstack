import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import '@/i18n';
import { useRouter } from 'next/router';
import { useEffect, useState } from 'react';
import Layout from '@/components/Layout';
import { getMe } from '@/utils/api';

const inter = Inter({ subsets: ['latin'] });

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const publicRoutes = ['/login', '/register'];
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    if (publicRoutes.includes(router.pathname)) {
      setChecking(false);
      return;
    }
    getMe()
      .then(() => setChecking(false))
      .catch(() => {
        router.replace('/login');
      });
  }, [router.pathname, router]);

  if (checking) return null;

  const content = <Component {...pageProps} />;
  return (
    <div className={inter.className}>
      {publicRoutes.includes(router.pathname) ? content : <Layout>{content}</Layout>}
    </div>
  );
}

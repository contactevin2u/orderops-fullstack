import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import '@/i18n';
import { useRouter } from 'next/router';
import { AppLayout as Layout } from '@/components/Layout';
import React from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const inter = Inter({ subsets: ['latin'] });

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const noLayout = ['/login', '/register'];
  const content = <Component {...pageProps} />;
  const queryClient = React.useMemo(() => new QueryClient(), []);
  return (
    <QueryClientProvider client={queryClient}>
      <div className={inter.className}>
        {noLayout.includes(router.pathname) ? content : <Layout>{content}</Layout>}
      </div>
    </QueryClientProvider>
  );
}

import type { AppProps } from 'next/app';
import type { Session } from 'next-auth';
import { SessionProvider } from 'next-auth/react';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import '@/i18n';
import { useRouter } from 'next/router';
import Layout from '@/components/Layout';

const inter = Inter({ subsets: ['latin'] });

export default function App({
  Component,
  pageProps: { session, ...pageProps },
}: AppProps<{ session: Session | null }>) {
  const router = useRouter();
  const noLayout = ['/login', '/register'];
  const content = <Component {...pageProps} />;
  return (
    <SessionProvider session={session}>
      <div className={inter.className}>
        {noLayout.includes(router.pathname) ? content : <Layout>{content}</Layout>}
      </div>
    </SessionProvider>
  );
}

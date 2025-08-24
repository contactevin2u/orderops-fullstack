import type { AppProps } from 'next/app';
import { Inter } from 'next/font/google';
import '@/styles/globals.css';
import '@/i18n';
import { useRouter } from 'next/router';
import AppShell from '@/components/AppShell';

const inter = Inter({ subsets: ['latin'] });

export default function App({ Component, pageProps }: AppProps) {
  const router = useRouter();
  const noLayout = ['/login', '/register'];


  const noLayout = ['/login', '/register'];

  const noLayout = ['/login'];

  const content = <Component {...pageProps} />;
  return (
    <div className={inter.className}>
      {noLayout.includes(router.pathname) ? content : <AppShell>{content}</AppShell>}
    </div>
  );
}

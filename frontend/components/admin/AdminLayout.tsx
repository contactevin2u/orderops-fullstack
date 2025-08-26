import React from 'react';
import { useRouter } from 'next/router';
import AdminNav from './AdminNav';

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const mainRef = React.useRef<HTMLElement>(null);
  const router = useRouter();

  React.useEffect(() => {
    mainRef.current?.focus();
  }, [router.asPath]);

  return (
    <>
      <a href="#admin-main" className="sr-only not-sr-only">Skip to content</a>
      <header>
        <AdminNav />
      </header>
      <main id="admin-main" tabIndex={-1} ref={mainRef} style={{ padding: 16 }}>
        {children}
      </main>
    </>
  );
}

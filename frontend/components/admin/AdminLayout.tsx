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
    <div className="layout">
      <a href="#admin-main" className="sr-only not-sr-only" style={{
        position: 'absolute',
        top: 'var(--space-4)',
        left: 'var(--space-4)',
        background: 'var(--color-primary)',
        color: 'var(--color-surface)',
        padding: 'var(--space-3) var(--space-2)',
        borderRadius: 'var(--radius-2)',
        zIndex: 50,
        textDecoration: 'none'
      }}>
        Skip to content
      </a>
      <header className="header">
        <AdminNav />
      </header>
      <main 
        id="admin-main" 
        tabIndex={-1} 
        ref={mainRef} 
        className="main"
        style={{ outline: 'none' }}
      >
        {children}
      </main>
    </div>
  );
}

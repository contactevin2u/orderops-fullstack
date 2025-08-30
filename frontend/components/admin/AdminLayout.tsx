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
    <div className="min-h-screen bg-gray-50">
      <a href="#admin-main" className="sr-only focus:not-sr-only focus:absolute focus:top-4 focus:left-4 bg-blue-600 text-white px-3 py-2 rounded-md z-50">
        Skip to content
      </a>
      <header className="bg-white border-b border-gray-200 sticky top-0 z-40">
        <AdminNav />
      </header>
      <main 
        id="admin-main" 
        tabIndex={-1} 
        ref={mainRef} 
        className="container mx-auto px-4 py-6 focus:outline-none"
      >
        {children}
      </main>
    </div>
  );
}

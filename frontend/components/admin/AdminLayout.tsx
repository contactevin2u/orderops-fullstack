import React from 'react';
import AdminNav from './AdminNav';

export default function AdminLayout({ children }:{children:React.ReactNode}){
  return (
    <div>
      <AdminNav />
      <main style={{padding:16}}>{children}</main>
    </div>
  );
}

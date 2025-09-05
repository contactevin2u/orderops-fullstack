import React, { useState } from 'react';
import Link from 'next/link';
import AdminLayout from '@/components/Layout/AdminLayout';

export default function AdminUsersPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('CASHIER');
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    
    if (!username.trim() || !password.trim()) {
      setMessage({ type: 'error', text: 'Username and password are required' });
      return;
    }

    const res = await fetch('/_api/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username: username.trim(), password, role }),
    });
    
    if (res.ok) {
      setMessage({ type: 'success', text: `${role.toLowerCase()} account created successfully` });
      setUsername('');
      setPassword('');
    } else {
      const data = await res.json().catch(() => ({}));
      setMessage({ type: 'error', text: data?.detail || 'Registration failed' });
    }
  }

  return (
    <div className="main">
      <div className="container small-container">
        <div style={{ marginBottom: 'var(--space-6)' }}>
          <h1 style={{ fontSize: '1.5rem', fontWeight: 700, marginBottom: 'var(--space-2)' }}>User Management</h1>
          <p style={{ opacity: 0.8 }}>
            Create admin and cashier accounts for the web application. 
            For drivers, use the <Link href="/admin/drivers" style={{ color: 'var(--color-primary)', textDecoration: 'underline' }}>Drivers section</Link> instead.
          </p>
        </div>

        {message && (
          <div
            style={{
              marginBottom: 'var(--space-6)',
              padding: 'var(--space-4)',
              borderRadius: 'var(--radius-2)',
              border: '1px solid',
              ...(message.type === 'success' 
                ? { background: '#f0fdf4', color: '#15803d', borderColor: '#bbf7d0' }
                : { background: '#fef2f2', color: '#dc2626', borderColor: '#fecaca' })
            }}
            role="alert"
          >
            {message.text}
          </div>
        )}

        <div className="card">
          <h2 style={{ fontSize: '1.125rem', fontWeight: 600, marginBottom: 'var(--space-4)' }}>Create New User</h2>
          
          <form onSubmit={onSubmit} className="stack">
            <div>
              <label htmlFor="username" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
                Username *
              </label>
              <input
                id="username"
                type="text"
                className="input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                placeholder="Enter username"
              />
            </div>
            
            <div>
              <label htmlFor="password" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
                Password *
              </label>
              <input
                id="password"
                type="password"
                className="input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                placeholder="Enter secure password"
                minLength={6}
              />
            </div>
            
            <div>
              <label htmlFor="role" style={{ display: 'block', fontSize: '0.875rem', fontWeight: 500, marginBottom: 'var(--space-1)' }}>
                Role *
              </label>
              <select
                id="role"
                className="select"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="CASHIER">Cashier - Can process payments and view orders</option>
                <option value="ADMIN">Admin - Full access to all features</option>
              </select>
              <p style={{ marginTop: 'var(--space-1)', fontSize: '0.875rem', opacity: 0.7 }}>
                Note: Driver accounts should be created in the Drivers section for mobile app access
              </p>
            </div>
            
            <button
              type="submit"
              className="btn"
            >
              Create User
            </button>
          </form>
        </div>

        <div style={{
          marginTop: 'var(--space-6)',
          padding: 'var(--space-4)',
          background: '#eff6ff',
          borderRadius: 'var(--radius-2)',
          border: '1px solid #dbeafe'
        }}>
          <h3 style={{ fontWeight: 500, color: '#1e40af', marginBottom: 'var(--space-2)' }}>💡 User Types</h3>
          <div className="stack" style={{ fontSize: '0.875rem', color: '#1e40af' }}>
            <p><strong>Admin:</strong> Full access to all features including user management, driver management, and system settings</p>
            <p><strong>Cashier:</strong> Access to payment processing, order viewing, and basic operations</p>
            <p><strong>Driver:</strong> Mobile app access only - create these in the Drivers section</p>
          </div>
        </div>
      </div>
    </div>
  );
}

(AdminUsersPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

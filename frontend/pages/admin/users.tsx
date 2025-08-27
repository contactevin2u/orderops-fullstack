import React, { useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';

export default function AdminUsersPage() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [role, setRole] = useState('CASHIER');
  const [message, setMessage] = useState<string | null>(null);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setMessage(null);
    const res = await fetch('/_api/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, role }),
    });
    if (res.ok) {
      setMessage('User created');
      setUsername('');
      setPassword('');
    } else {
      const data = await res.json().catch(() => ({}));
      setMessage(data?.detail || 'Registration failed');
    }
  }

  return (
    <div>
      <h1>Create User</h1>
      <form className="stack" style={{ maxWidth: 320 }} onSubmit={onSubmit}>
        <label>
          Username
          <input value={username} onChange={(e) => setUsername(e.target.value)} required />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
          />
        </label>
        <label>
          Role
          <select value={role} onChange={(e) => setRole(e.target.value)}>
            <option value="CASHIER">Cashier</option>
            <option value="ADMIN">Admin</option>
            <option value="DRIVER">Driver</option>
          </select>
        </label>
        {message && <p>{message}</p>}
        <button className="btn" type="submit">Create</button>
      </form>
    </div>
  );
}

(AdminUsersPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

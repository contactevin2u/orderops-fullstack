import React, { useState } from 'react';
import AdminLayout from '@/components/admin/AdminLayout';

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
    <div className="max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold mb-2">User Management</h1>
        <p className="text-gray-600">
          Create admin and cashier accounts for the web application. 
          For drivers, use the <a href="/admin/drivers" className="text-blue-600 hover:underline">Drivers section</a> instead.
        </p>
      </div>

      {message && (
        <div
          className={`mb-6 p-4 rounded-md ${
            message.type === 'success'
              ? 'bg-green-50 text-green-700 border border-green-200'
              : 'bg-red-50 text-red-700 border border-red-200'
          }`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      <div className="bg-white rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-4">Create New User</h2>
        
        <form onSubmit={onSubmit} className="space-y-4">
          <div>
            <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-1">
              Username *
            </label>
            <input
              id="username"
              type="text"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              placeholder="Enter username"
            />
          </div>
          
          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              Password *
            </label>
            <input
              id="password"
              type="password"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              placeholder="Enter secure password"
              minLength={6}
            />
          </div>
          
          <div>
            <label htmlFor="role" className="block text-sm font-medium text-gray-700 mb-1">
              Role *
            </label>
            <select
              id="role"
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              value={role}
              onChange={(e) => setRole(e.target.value)}
            >
              <option value="CASHIER">Cashier - Can process payments and view orders</option>
              <option value="ADMIN">Admin - Full access to all features</option>
            </select>
            <p className="mt-1 text-sm text-gray-500">
              Note: Driver accounts should be created in the Drivers section for mobile app access
            </p>
          </div>
          
          <button
            type="submit"
            className="w-full sm:w-auto btn"
          >
            Create User
          </button>
        </form>
      </div>

      <div className="mt-6 p-4 bg-blue-50 rounded-lg border border-blue-200">
        <h3 className="font-medium text-blue-800 mb-2">💡 User Types</h3>
        <div className="space-y-2 text-sm text-blue-700">
          <p><strong>Admin:</strong> Full access to all features including user management, driver management, and system settings</p>
          <p><strong>Cashier:</strong> Access to payment processing, order viewing, and basic operations</p>
          <p><strong>Driver:</strong> Mobile app access only - create these in the Drivers section</p>
        </div>
      </div>
    </div>
  );
}

(AdminUsersPage as any).getLayout = (page: any) => <AdminLayout>{page}</AdminLayout>;

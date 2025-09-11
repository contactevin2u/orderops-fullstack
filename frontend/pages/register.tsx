import React from 'react';
import { useTranslation } from 'react-i18next';

export default function RegisterPage() {
  const { t } = useTranslation();
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [error, setError] = React.useState('');

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const res = await fetch('https://orderops-api-v1.onrender.com/auth/register', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      window.location.href = '/login';
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data?.detail || 'Registration failed');
    }
  }

  return (
    <div className="container" style={{ maxWidth: '20rem', marginTop: '4rem' }}>
      <form className="stack" onSubmit={onSubmit}>
        <h2>{t('register.title', { defaultValue: 'Create Account' })}</h2>
        <input
          className="input"
          placeholder={t('register.username', { defaultValue: 'Username' }) as string}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="input"
          placeholder={t('register.password', { defaultValue: 'Password' }) as string}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        {error && <p style={{ color: '#ff4d4f' }}>{error}</p>}
        <button className="button" type="submit">
          {t('register.submit', { defaultValue: 'Register' })}
        </button>
      </form>
    </div>
  );
}

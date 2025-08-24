import React from 'react';
import Link from 'next/link';
import { useTranslation } from 'react-i18next';

export default function LoginPage() {
  const { t } = useTranslation();
  const [username, setUsername] = React.useState('');
  const [password, setPassword] = React.useState('');
  const [remember, setRemember] = React.useState(false);
  const [error, setError] = React.useState('');

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError('');
    const res = await fetch('/_api/auth/login', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, remember }),
    });
    if (res.ok) {
      window.location.href = '/';
    } else {
      const data = await res.json().catch(() => ({}));
      setError(data?.detail || 'Login failed');
    }
  }

  return (
    <div className="container" style={{ maxWidth: '20rem', marginTop: '4rem' }}>
      <form className="stack" onSubmit={onSubmit}>
        <h2>{t('login.title', { defaultValue: 'Sign In' })}</h2>
        <input
          className="input"
          placeholder={t('login.username', { defaultValue: 'Username' }) as string}
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
        <input
          type="password"
          className="input"
          placeholder={t('login.password', { defaultValue: 'Password' }) as string}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
        <label style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
          {t('login.remember', { defaultValue: 'Remember me' })}
        </label>
        {error && <p style={{ color: '#ff4d4f' }}>{error}</p>}
        <button className="button" type="submit">
          {t('login.submit', { defaultValue: 'Login' })}
        </button>

        <p style={{ textAlign: 'center' }}>
          <Link href="/register">
            {t('login.register', { defaultValue: 'Create an account' })}
          </Link>
        </p>

        </form>
    </div>
  );
}


import { useState } from 'react';
import { useRouter } from 'next/router';

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      const res = await fetch('/_api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ username, password, remember }),
      });
      if (!res.ok) {
        const msg = (await res.json().catch(() => null))?.detail || 'Invalid credentials';
        setError(msg);
        return;
      }
      router.replace('/');
    } catch (e: any) {
      setError(e.message || 'Login failed');
    }
  }

  return (
    <div className="container small-container" style={{ marginTop: '4rem' }}>
      <form className="stack" onSubmit={handleSubmit}>
        <h1>Sign in</h1>
        <label>
          Username
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            required
          />
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
        <label className="cluster" style={{ alignItems: 'center' }}>
          <input
            type="checkbox"
            checked={remember}
            onChange={(e) => setRemember(e.target.checked)}
          />
          Remember me
        </label>
        <button className="primary" type="submit">
          Sign in
        </button>
        {error && <p className="error">{error}</p>}
      </form>
    </div>
  );
}


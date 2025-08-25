import { signIn } from 'next-auth/react';

export default function LoginPage() {
  const handleSignIn = () => signIn('github').catch(() => signIn());
  return (
    <div className="container" style={{ maxWidth: '20rem', marginTop: '4rem' }}>
      <div className="stack">
        <h1>Sign in</h1>
        <p>Use your GitHub account to continue.</p>
        <button className="button" onClick={handleSignIn}>
          Sign in with GitHub
        </button>
      </div>
    </div>
  );
}


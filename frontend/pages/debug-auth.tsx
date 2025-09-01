import { useState } from 'react';

export default function AuthDebugPage() {
  const [token, setToken] = useState('');
  const [decodedToken, setDecodedToken] = useState<any>(null);

  const checkToken = async () => {
    try {
      // Get token from cookie
      const cookies = document.cookie.split(';');
      const tokenCookie = cookies.find(c => c.trim().startsWith('token='));
      const cookieToken = tokenCookie ? tokenCookie.split('=')[1] : 'Not found';
      
      // Try to decode JWT (base64)
      if (cookieToken !== 'Not found') {
        const parts = cookieToken.split('.');
        if (parts.length === 3) {
          const payload = JSON.parse(atob(parts[1]));
          const now = Date.now() / 1000;
          setDecodedToken({
            ...payload,
            isExpired: payload.exp < now,
            expiresIn: Math.round(payload.exp - now),
            expiresAt: new Date(payload.exp * 1000).toLocaleString()
          });
        }
      }
      
      setToken(cookieToken);
    } catch (error) {
      console.error('Token check failed:', error);
      setDecodedToken({ error: error.message });
    }
  };

  const testAPI = async () => {
    try {
      const res = await fetch('/_api/auth/me', {
        credentials: 'include'
      });
      console.log('API Test:', res.status, await res.text());
    } catch (error) {
      console.error('API Test failed:', error);
    }
  };

  return (
    <div style={{ padding: '20px', fontFamily: 'monospace' }}>
      <h1>Auth Debug Page</h1>
      
      <button onClick={checkToken}>Check Token</button>
      <button onClick={testAPI} style={{ marginLeft: '10px' }}>Test API</button>
      
      <h3>Token Status:</h3>
      <pre>{token}</pre>
      
      {decodedToken && (
        <>
          <h3>Decoded Token:</h3>
          <pre>{JSON.stringify(decodedToken, null, 2)}</pre>
        </>
      )}
      
      <h3>Browser Info:</h3>
      <pre>{`
Domain: ${location.hostname}
Protocol: ${location.protocol}
User Agent: ${navigator.userAgent}
Cookies Enabled: ${navigator.cookieEnabled}
      `}</pre>
    </div>
  );
}
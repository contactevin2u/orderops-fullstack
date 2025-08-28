import React from 'react';
import auth from '@react-native-firebase/auth';
import { setTokenGetter } from './src/lib/api';
import { OutboxProvider, useOutbox } from './src/offline/useOutbox';
import Toast from './src/components/Toast';
import { useAuth } from './src/hooks/useAuth';
import { useNotifications } from './src/hooks/useNotifications';
import { useNetwork } from './src/hooks/useNetwork';
import { OfflineBanner } from './src/components/OfflineBanner';
import Login from './src/screens/Login';
import Home from './src/screens/Home';

setTokenGetter(async () => {
  const current = auth().currentUser;
  return current ? await current.getIdToken() : undefined;
});

function AuthedApp() {
  useNotifications();
  return <Home />;
}

function InnerApp({ user }: { user: any }) {
  const { online } = useNetwork();
  const { pending } = useOutbox();
  return (
    <>
      <Toast />
      <OfflineBanner online={online} pendingCount={pending} />
      {user ? <AuthedApp /> : <Login />}
    </>
  );
}

export default function App() {
  const { user } = useAuth();
  return (
    <OutboxProvider>
      <InnerApp user={user} />
    </OutboxProvider>
  );
}


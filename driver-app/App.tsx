import React from 'react';
import auth from '@react-native-firebase/auth';
import { setTokenGetter } from './src/lib/api';
import { OutboxProvider } from './src/offline/useOutbox';
import Toast from './src/components/Toast';
import { useAuth } from './src/hooks/useAuth';
import { useNotifications } from './src/hooks/useNotifications';
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

export default function App() {
  const { user } = useAuth();
  return (
    <OutboxProvider>
      <Toast />
      {user ? <AuthedApp /> : <Login />}
    </OutboxProvider>
  );
}


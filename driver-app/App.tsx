import React from 'react';
import { useAuth } from './src/hooks/useAuth';
import { useNotifications } from './src/hooks/useNotifications';
import Login from './src/screens/Login';
import Home from './src/screens/Home';

export default function App() {
  const { user } = useAuth();
  useNotifications();
  return user ? <Home /> : <Login />;
}

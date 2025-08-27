import { useCallback, useEffect, useRef, useState } from 'react';
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth';
import messaging from '@react-native-firebase/messaging';
import { Platform } from 'react-native';
import { api } from '../lib/api';

interface AuthHook {
  user: FirebaseAuthTypes.User | null;
  idToken: string | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthHook {
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null);
  const [idToken, setIdToken] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const registeredRef = useRef(false);

  const registerDevice = useCallback(async (idt: string) => {
    try {
      await messaging().requestPermission();
    } catch {}
    try {
      const token = await messaging().getToken();
      await api.post('/drivers/devices', idt, { token, platform: Platform.OS });
    } catch {}
  }, []);

  useEffect(() => {
    const unsub = auth().onIdTokenChanged(async (current) => {
      setUser(current);
      if (current) {
        const t = await current.getIdToken();
        setIdToken(t);
      } else {
        setIdToken(null);
        registeredRef.current = false;
      }
    });
    return unsub;
  }, []);

  useEffect(() => {
    if (user && idToken && !registeredRef.current) {
      registerDevice(idToken);
      registeredRef.current = true;
    }
  }, [user, idToken, registerDevice]);

  useEffect(() => {
    const sub = messaging().onTokenRefresh(async (fcmToken) => {
      const current = auth().currentUser;
      if (!current) return;
      const t = await current.getIdToken(true);
      setIdToken(t);
      try {
        await api.post('/drivers/devices', t, { token: fcmToken, platform: Platform.OS });
      } catch {}
    });
    return sub;
  }, []);

  const signIn = useCallback(async (email: string, password: string) => {
    setLoading(true);
    try {
      await auth().signInWithEmailAndPassword(email.trim(), password);
    } finally {
      setLoading(false);
    }
  }, []);

  const signOut = useCallback(async () => {
    await auth().signOut();
  }, []);

  return { user, idToken, loading, signIn, signOut };
}

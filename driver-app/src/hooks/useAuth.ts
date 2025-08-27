import { useCallback, useEffect, useRef, useState } from 'react';
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth';
import messaging from '@react-native-firebase/messaging';
import { Platform } from 'react-native';
import { api } from '../lib/api';

interface AuthHook {
  user: FirebaseAuthTypes.User | null;
  loading: boolean;
  signIn: (email: string, password: string) => Promise<void>;
  signOut: () => Promise<void>;
}

export function useAuth(): AuthHook {
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null);
  const [loading, setLoading] = useState(false);
  const registeredRef = useRef(false);

  const registerDevice = useCallback(async () => {
    try {
      await messaging().requestPermission();
    } catch {}
    try {
      const token = await messaging().getToken();
      await api.post('/drivers/devices', { token, platform: Platform.OS });
    } catch {}
  }, []);

  useEffect(() => {
    const unsub = auth().onAuthStateChanged(async (current) => {
      setUser(current);
      if (current) {
        if (!registeredRef.current) {
          registerDevice();
          registeredRef.current = true;
        }
      } else {
        registeredRef.current = false;
      }
    });
    return unsub;
  }, [registerDevice]);

  useEffect(() => {
    const sub = messaging().onTokenRefresh(async (fcmToken) => {
      const current = auth().currentUser;
      if (!current) return;
      try {
        await api.post('/drivers/devices', { token: fcmToken, platform: Platform.OS });
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

  return { user, loading, signIn, signOut };
}

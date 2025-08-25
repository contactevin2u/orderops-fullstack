import React, { useEffect, useState, useCallback } from 'react';
import {
  ScrollView,
  View,
  Text,
  Platform,
  Pressable,
  TextInput,
  Alert,
} from 'react-native';
import Constants from 'expo-constants';
import messaging from '@react-native-firebase/messaging';
import auth, { FirebaseAuthTypes } from '@react-native-firebase/auth';
import OrderItem from './src/components/OrderItem';
import { useOrderStore } from './src/stores/orderStore';

type Status = string | null;

const API_BASE =
  (Constants?.expoConfig?.extra as any)?.apiBase ||
  'https://orderops-api-v1.onrender.com';

// Only show debug diagnostics in development builds
const DEBUG = __DEV__;

export default function App() {
  const [health, setHealth] = useState<Status>(null);
  const [uid, setUid] = useState<Status>(null);
  const [idToken, setIdToken] = useState<Status>(null);
  const [fcm, setFcm] = useState<Status>(null);
  const [registerStatus, setRegisterStatus] = useState<Status>(null);
  const [error, setError] = useState<Status>(null);
  const [user, setUser] = useState<FirebaseAuthTypes.User | null>(null);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [loginError, setLoginError] = useState<Status>(null);
  const [signingIn, setSigningIn] = useState(false);
  const orders = useOrderStore((s) => s.orders);
  const setOrders = useOrderStore((s) => s.setOrders);
  const activeOrders = orders.filter((o) => o.status !== 'DELIVERED');
  const completedOrders = orders.filter((o) => o.status === 'DELIVERED');
  const [tab, setTab] = useState<'active' | 'completed'>('active');

  const checkHealth = useCallback(async () => {
    async function ping(path: string) {
      const r = await fetch(`${API_BASE}${path}`, { method: 'GET' });
      return `${r.status} ${r.statusText}`;
    }
    try {
      let status = await ping('/healthz');
      if (status.startsWith('404')) status = await ping('/health');
      setHealth(status);
    } catch (e: any) {
      setHealth(`Network error: ${e?.message ?? String(e)}`);
    }
  }, []);
  const fetchOrders = useCallback(
    async (token: string) => {
      try {
        const r = await fetch(`${API_BASE}/drivers/orders`, {
          method: 'GET',
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) {
          const data = await r.json();
          setOrders(data?.data ?? data);
        }
      } catch (e) {
        // ignore fetch errors for now
      }
    },
    [setOrders]
  );

  const handleOrderAssigned = useCallback(
    async (msg: any) => {
      if (msg?.data?.type === 'order_assigned') {
        await fetchOrders(idToken ?? '');
        try {
          Alert.alert('New order assigned');
        } catch {}
      }
    },
    [fetchOrders, idToken]
  );

  const bootstrap = useCallback(async () => {
    setError(null);
    const current = auth().currentUser;
    if (!current) return;
    try {
      setUid(current.uid);

      // 1) Notifications permission (Android 13+ / iOS)
      try {
        await messaging().requestPermission();
      } catch {}

      // 2) Get FCM token
      const token = await messaging().getToken();
      setFcm(token);

      // 3) Get ID token to authenticate with your backend
      const idt = await current.getIdToken(true);
      setIdToken(idt);

      // 4) Register device with backend
      setRegisterStatus('registering…');
      const res = await fetch(`${API_BASE}/drivers/devices/register`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${idt}`,
        },
        body: JSON.stringify({ fcm_token: token, platform: Platform.OS }),
      });
      setRegisterStatus(res.ok ? 'OK' : `Failed: ${res.status}`);

      // 5) Fetch assigned orders
      if (res.ok) await fetchOrders(idt);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    }
  }, [fetchOrders]);

  const login = useCallback(async () => {
    if (signingIn) return;
    setLoginError(null);
    setSigningIn(true);
    try {
      await auth().signInWithEmailAndPassword(email.trim(), password);
    } catch (e: any) {
      setLoginError(e?.message ?? String(e));
    } finally {
      setSigningIn(false);
    }
  }, [email, password, signingIn]);

  useEffect(() => {
    const sub = auth().onAuthStateChanged(setUser);
    return sub;
  }, []);

  useEffect(() => {
    const sub = messaging().onMessage(handleOrderAssigned);
    return sub;
  }, [handleOrderAssigned]);

  useEffect(() => {
    const sub = messaging().onNotificationOpenedApp(handleOrderAssigned);
    messaging()
      .getInitialNotification()
      .then((msg) => {
        if (msg) handleOrderAssigned(msg);
      });
    return sub;
  }, [handleOrderAssigned]);

  useEffect(() => {
    if (user) {
      checkHealth();
      bootstrap();
    }
  }, [user, checkHealth, bootstrap]);
  if (!user) {
    return (
      <View style={styles.loginContainer}>
        <Text style={styles.title}>Driver Login</Text>
        <TextInput
          style={styles.input}
          placeholder="Email"
          autoCapitalize="none"
          keyboardType="email-address"
          value={email}
          onChangeText={setEmail}
        />
        <TextInput
          style={styles.input}
          placeholder="Password"
          secureTextEntry
          value={password}
          onChangeText={setPassword}
          returnKeyType="done"
          onSubmitEditing={login}
        />
        {loginError && <Text style={styles.error}>Error: {loginError}</Text>}
        <Btn text={signingIn ? 'Signing In…' : 'Sign In'} onPress={login} disabled={signingIn} />
      </View>
    );
  }

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Pressable style={styles.signOut} onPress={() => auth().signOut()}>
        <Text style={styles.signOutText}>Sign Out</Text>
      </Pressable>
      {DEBUG && (
        <>
          <Row label="API Base" value={API_BASE} />
          <Row label="Health" value={health ?? '…'} />
          <Row label="Firebase UID" value={uid ?? '…'} />
          <Row label="ID Token (tail)" value={idToken ? tail(idToken) : '…'} />
          <Row label="FCM Token (tail)" value={fcm ? tail(fcm) : '…'} />
          <Row label="Register" value={registerStatus ?? '…'} />
          {error && <Text style={styles.error}>Error: {error}</Text>}

          <View style={{ height: 12 }} />
          <Btn text="Retry Health" onPress={checkHealth} />
          <View style={{ height: 8 }} />
          <Btn text="Re-run Auth + Register" onPress={bootstrap} />
          <View style={{ height: 8 }} />
        </>
      )}
      <View style={styles.tabs}>
        <Pressable
          style={[styles.tab, tab === 'active' && styles.tabActive]}
          onPress={() => setTab('active')}
        >
          <Text style={[styles.tabText, tab === 'active' && styles.tabTextActive]}>
            Active ({activeOrders.length})
          </Text>
        </Pressable>
        <Pressable
          style={[styles.tab, tab === 'completed' && styles.tabActive]}
          onPress={() => setTab('completed')}
        >
          <Text style={[styles.tabText, tab === 'completed' && styles.tabTextActive]}>
            Completed ({completedOrders.length})
          </Text>
        </Pressable>
      </View>
      {tab === 'active' ? (
        activeOrders.length === 0 ? (
          <Text>No active orders.</Text>
        ) : (
          activeOrders.map((o) => (
            <OrderItem
              key={o.id}
              order={o}
              token={idToken ?? ''}
              apiBase={API_BASE}
              refresh={() => fetchOrders(idToken ?? '')}
            />
          ))
        )
      ) : completedOrders.length === 0 ? (
        <Text>No completed orders.</Text>
      ) : (
        completedOrders.map((o) => (
          <OrderItem
            key={o.id}
            order={o}
            token={idToken ?? ''}
            apiBase={API_BASE}
            refresh={() => fetchOrders(idToken ?? '')}
          />
        ))
      )}
    </ScrollView>
  );
}

/* ---------- helpers & styles ---------- */
function tail(s: string, n = 12) { return s.length <= n ? s : `…${s.slice(-n)}`; }
function Row({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.row}>
      <Text style={styles.label}>{label}</Text>
      <Text selectable style={styles.value}>{value}</Text>
    </View>
  );
}
function Btn({ text, onPress, disabled }: { text: string; onPress: () => void; disabled?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={disabled} style={[styles.button, disabled && { opacity: 0.5 }]}> 
      <Text style={styles.buttonText}>{text}</Text>
    </Pressable>
  );
}
const styles = {
  container: {
    flexGrow: 1 as const,
    padding: 16,
    backgroundColor: '#f0f9ff',
  },
  loginContainer: {
    flexGrow: 1 as const,
    padding: 16,
    justifyContent: 'center' as const,
    backgroundColor: '#f0f9ff',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center' as const,
    marginBottom: 16,
    color: '#0f172a',
  },
  row: { marginVertical: 6 },
  label: { fontSize: 12, color: '#64748b', marginBottom: 2 },
  value: { fontSize: 14, color: '#0f172a' },
  error: { marginTop: 12, color: '#b00020' },
  input: {
    borderWidth: 1,
    borderColor: '#93c5fd',
    backgroundColor: '#fff',
    borderRadius: 4,
    padding: 8,
    marginBottom: 12,
  },
  button: {
    backgroundColor: '#3b82f6',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center' as const,
  },
  buttonText: { color: '#fff', fontWeight: '600' as const },
  signOut: { alignSelf: 'flex-end' as const, padding: 4, marginBottom: 8 },
  signOutText: {
    color: '#3b82f6',
    fontSize: 12,
    textDecorationLine: 'underline' as const,
  },
  tabs: { flexDirection: 'row' as const, marginBottom: 16 },
  tab: {
    flex: 1,
    paddingVertical: 8,
    borderBottomWidth: 2,
    borderColor: '#e5e7eb',
    alignItems: 'center' as const,
  },
  tabActive: { borderColor: '#3b82f6' },
  tabText: { color: '#64748b' },
  tabTextActive: { color: '#3b82f6', fontWeight: '600' as const },
};

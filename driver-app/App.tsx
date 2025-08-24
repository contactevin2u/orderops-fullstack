import React, { useEffect, useState, useCallback } from 'react';
import { ScrollView, View, Text, Platform, Pressable } from 'react-native';
import Constants from 'expo-constants';
import messaging from '@react-native-firebase/messaging';
import auth from '@react-native-firebase/auth';
import OrderItem from './src/components/OrderItem';
import { useOrderStore } from './src/stores/orderStore';

type Status = string | null;

const API_BASE =
  (Constants?.expoConfig?.extra as any)?.apiBase ||
  'https://orderops-api-v1.onrender.com';

export default function App() {
  const [health, setHealth] = useState<Status>(null);
  const [uid, setUid] = useState<Status>(null);
  const [idToken, setIdToken] = useState<Status>(null);
  const [fcm, setFcm] = useState<Status>(null);
  const [registerStatus, setRegisterStatus] = useState<Status>(null);
  const [error, setError] = useState<Status>(null);
  const orders = useOrderStore((s) => s.orders);
  const setOrders = useOrderStore((s) => s.setOrders);

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

  const bootstrap = useCallback(async () => {
    setError(null);
    try {
      // 1) Firebase auth (anonymous = no SHA fingerprints required)
      if (!auth().currentUser) await auth().signInAnonymously();
      const user = auth().currentUser!;
      setUid(user.uid);

      // 2) Notifications permission (Android 13+ / iOS)
      try { await messaging().requestPermission(); } catch {}

      // 3) Get FCM token
      const token = await messaging().getToken();
      setFcm(token);

      // 4) Get ID token to authenticate with your backend
      const idt = await user.getIdToken(true);
      setIdToken(idt);

      // 5) Register device with backend
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

      // 6) Fetch assigned orders
      if (res.ok) await fetchOrders(idt);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    }
  }, [fetchOrders]);

  useEffect(() => {
    // optional foreground handler
    const sub = messaging().onMessage(async () => {});
    return sub;
  }, []);

  useEffect(() => { checkHealth(); bootstrap(); }, [checkHealth, bootstrap]);

  return (
    <ScrollView contentContainerStyle={styles.container}>
      <Text style={styles.title}>Driver App</Text>

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
      <View style={{ height: 24 }} />
      <Text style={styles.subtitle}>Assigned Orders</Text>
      {orders.length === 0 && <Text>No orders assigned.</Text>}
      {orders.map((o) => (
        <OrderItem key={o.id} order={o} />
      ))}
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
function Btn({ text, onPress }: { text: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} style={styles.button}>
      <Text style={styles.buttonText}>{text}</Text>
    </Pressable>
  );
}
const styles = {
  container: { flexGrow: 1 as const, padding: 16, justifyContent: 'center' as const, backgroundColor: '#fff' },
  title: { fontSize: 22, fontWeight: '700', textAlign: 'center' as const, marginBottom: 16 },
  subtitle: { fontSize: 18, fontWeight: '600', marginBottom: 8 },
  row: { marginVertical: 6 },
  label: { fontSize: 12, color: '#555', marginBottom: 2 },
  value: { fontSize: 14 },
  error: { marginTop: 12, color: '#b00020' },
  button: { backgroundColor: '#111827', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8, alignItems: 'center' as const },
  buttonText: { color: '#fff', fontWeight: '600' as const },
};

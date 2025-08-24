import React, { useEffect, useState, useCallback } from 'react';
import { ScrollView, View, Text, Platform, Pressable } from 'react-native';
import Constants from 'expo-constants';
import messaging from '@react-native-firebase/messaging';
import auth from '@react-native-firebase/auth';
import TripItem from './src/components/TripItem';
import { useTripStore } from './src/stores/tripStore';

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
  const trips = useTripStore((s) => s.trips);

  const checkHealth = useCallback(async () => {
    try {
      const r = await fetch(`${API_BASE}/health`, { method: 'GET' });
      setHealth(`${r.status} ${r.statusText}`);
    } catch (e: any) {
      setHealth(`Network error: ${e?.message ?? String(e)}`);
    }
  }, []);

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
      await useTripStore.getState().load(idt);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    }
  }, []);

  useEffect(() => {
    const sub = messaging().onMessage(async () => {
      if (idToken) await useTripStore.getState().load(idToken);
    });
    return sub;
  }, [idToken]);

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

      {trips.map((t) => (
        <TripItem key={t.id} trip={t} token={idToken || ''} />
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
  row: { marginVertical: 6 },
  label: { fontSize: 12, color: '#555', marginBottom: 2 },
  value: { fontSize: 14 },
  error: { marginTop: 12, color: '#b00020' },
  button: { backgroundColor: '#111827', paddingVertical: 10, paddingHorizontal: 14, borderRadius: 8, alignItems: 'center' as const },
  buttonText: { color: '#fff', fontWeight: '600' as const },
};

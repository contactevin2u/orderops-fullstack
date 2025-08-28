import messaging from '@react-native-firebase/messaging';
import notifee from '@notifee/react-native';
import { API_BASE } from 'src/shared/constants/config';

async function postToken(token: string) {
  await fetch(`${API_BASE}/drivers/devices`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ token }),
  });
}

export async function registerDevice() {
  await messaging().requestPermission();
  await notifee.requestPermission();
  const token = await messaging().getToken();
  await postToken(token);
  messaging().onTokenRefresh(postToken);
}

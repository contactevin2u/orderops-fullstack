import { registerRootComponent } from 'expo';
import App from './App';
import messaging from '@react-native-firebase/messaging';
import notifee from '@notifee/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

// background handler (required for notifications when app is quit)
messaging().setBackgroundMessageHandler(async (msg) => {
  const t = msg?.data?.type;
  if (t === 'order_assigned' || t === 'trip_assignment') {
    // 1) show a system notification
    await notifee.displayNotification({
      title: 'New order assigned',
      body: 'Tap to open and view.',
      android: { channelId: 'orders' },
    });
    // 2) OPTIONAL: headless fetch to stash new orders for instant UI
    try {
      const idt = await AsyncStorage.getItem('idToken');
      const apiBase = 'https://orderops-api-v1.onrender.com';
      if (idt) {
        const r = await fetch(`${apiBase}/drivers/orders`, {
          method: 'GET',
          headers: { Authorization: `Bearer ${idt}` },
        });
        if (r.ok) {
          const data = await r.json();
          await AsyncStorage.setItem('pendingOrders', JSON.stringify(data?.data ?? data));
        }
      }
    } catch {}
  }
});

registerRootComponent(App);

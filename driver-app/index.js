import { registerRootComponent } from 'expo';
import App from './App';
import messaging from '@react-native-firebase/messaging';
import notifee from '@notifee/react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { api } from './src/lib/api';

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
      const r = await api.get('/drivers/orders');
      if (r.ok) {
        await AsyncStorage.setItem('pendingOrders', JSON.stringify(r.data?.data ?? r.data));
      }
    } catch {}
  }
});

registerRootComponent(App);

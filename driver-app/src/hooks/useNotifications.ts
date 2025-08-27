import { useEffect } from 'react';
import messaging from '@react-native-firebase/messaging';
import notifee, { AndroidImportance } from '@notifee/react-native';
import { useOrders } from './useOrders';

export function useNotifications() {
  const { refresh } = useOrders({ skipPolling: true });

  useEffect(() => {
    notifee.createChannel({
      id: 'orders',
      name: 'Order Assignments',
      importance: AndroidImportance.HIGH,
    }).catch(() => {});
  }, []);

  useEffect(() => {
    const handler = async (msg: any) => {
      const t = msg?.data?.type;
      if (t === 'order_assigned' || t === 'trip_assignment') {
        await refresh();
        try {
          await notifee.displayNotification({
            title: 'New order assigned',
            body: 'You have a new delivery task.',
            android: { channelId: 'orders' },
          });
        } catch {}
      }
    };
    const fg = messaging().onMessage(handler);
    const opened = messaging().onNotificationOpenedApp(handler);
    messaging().getInitialNotification().then((m) => {
      if (m) handler(m);
    });
    return () => {
      fg();
      opened();
    };
  }, [refresh]);
}

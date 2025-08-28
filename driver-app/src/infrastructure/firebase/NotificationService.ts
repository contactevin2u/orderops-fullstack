import messaging from "@react-native-firebase/messaging";
import notifee, { EventType } from "@notifee/react-native";
import { API_BASE } from "@shared/constants/config";
import { emit } from "@infra/events/bus";
import { ORDER_OPEN_EVENT } from "@infra/events/bus";

async function postToken(token: string) {
  await fetch(`${API_BASE}/drivers/devices`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
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

export async function initNotifications() {
  await notifee.createChannel({ id: "orders", name: "Orders" });
  messaging().onMessage(async (msg) => {
    await notifee.displayNotification({
      title: msg.notification?.title,
      body: msg.notification?.body,
      android: { channelId: "orders" },
      data: msg.data as Record<string, string> | undefined,
    });
  });
  notifee.onForegroundEvent((event) => {
    if (event.type === EventType.PRESS) {
      const orderId = event.detail.notification?.data?.orderId;
      if (orderId) {
        emit(ORDER_OPEN_EVENT, { orderId });
      }
    }
  });
  notifee.onBackgroundEvent(async (event) => {
    if (event.type === EventType.PRESS) {
      const orderId = event.detail.notification?.data?.orderId;
      if (orderId) {
        emit(ORDER_OPEN_EVENT, { orderId });
      }
    }
  });
}


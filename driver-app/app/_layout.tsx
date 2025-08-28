import { Slot } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaView, StatusBar } from "react-native";
import { useEffect } from "react";
import { useRouter } from "expo-router";
import {
  registerDevice,
  initNotifications,
  onNotificationOpenOrder,
} from "src/infrastructure/firebase/NotificationService";

const queryClient = new QueryClient();

export default function RootLayout() {
  const router = useRouter();
  useEffect(() => {
    registerDevice().catch(() => {
      // swallow registration errors during bootstrap
    });
    initNotifications().catch(() => {});
    const sub = onNotificationOpenOrder((orderId) => {
      router.push(`/order/${orderId}`);
      // TODO: invalidate orders query when React Query wiring is ready
    });
    return sub;
  }, [router]);
  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaView style={{ flex: 1 }}>
        <StatusBar />
        <Slot />
      </SafeAreaView>
    </QueryClientProvider>
  );
}

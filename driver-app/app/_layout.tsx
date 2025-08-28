import { Slot } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaView, StatusBar } from "react-native";
import { useEffect } from "react";
import { useRouter } from "expo-router";
import { registerDevice, initNotifications } from "@infra/firebase/NotificationService";
import { on, ORDER_OPEN_EVENT } from "@infra/events/bus";

const queryClient = new QueryClient();

export default function RootLayout() {
  const router = useRouter();
  useEffect(() => {
    registerDevice().catch(() => {
      // swallow registration errors during bootstrap
    });
    initNotifications().catch(() => {});
    const off = on(ORDER_OPEN_EVENT, ({ orderId }: { orderId: string }) => {
      router.push(`/order/${orderId}`);
      try {
        queryClient.invalidateQueries({ queryKey: ["orders"] });
      } catch {
        // ignore if query client not available
      }
    });
    return off;
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

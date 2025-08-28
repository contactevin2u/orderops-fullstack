import { Slot } from "expo-router";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaView, StatusBar } from "react-native";
import { useEffect } from "react";
import { registerDevice } from "src/infrastructure/firebase/notifications";

const queryClient = new QueryClient();

export default function RootLayout() {
  useEffect(() => {
    registerDevice().catch(() => {
      // swallow registration errors during bootstrap
    });
  }, []);
  return (
    <QueryClientProvider client={queryClient}>
      <SafeAreaView style={{ flex: 1 }}>
        <StatusBar />
        <Slot />
      </SafeAreaView>
    </QueryClientProvider>
  );
}

import { ExpoConfig } from "@expo/config";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  const apiBase = process.env.API_BASE || process.env.EXPO_PUBLIC_API_BASE;
  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    plugins: [
      ...(config.plugins ?? []),
      "@react-native-firebase/app",
      "@react-native-firebase/messaging",
      "@notifee/react-native",
    ],
    extra: {
      API_BASE: apiBase,
    },
  };
};

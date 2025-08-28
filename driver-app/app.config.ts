import { ExpoConfig } from "@expo/config";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    extra: {
      API_BASE: process.env.EXPO_PUBLIC_API_BASE,
    },
  };
};

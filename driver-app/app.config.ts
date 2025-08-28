import { ExpoConfig } from "@expo/config";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  const apiBase = process.env.API_BASE || process.env.EXPO_PUBLIC_API_BASE;
  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    extra: {
      API_BASE: apiBase,
    },
  };
};

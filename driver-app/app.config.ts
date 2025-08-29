import { ExpoConfig } from "@expo/config";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  const android: ExpoConfig["android"] = {
    ...config.android,
    package: "com.yourco.driverAA",
    googleServicesFile: "./google-services.json",
  };

  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    scheme: "driver",
    plugins: [
      ...(config.plugins ?? []),
      ["expo-build-properties", { android: { kotlinVersion: "1.9.24" } }],
      "@react-native-firebase/app",
      "@react-native-firebase/messaging",
      "@notifee/react-native",
    ],
    extra: {
      API_BASE: process.env.API_BASE,
      FIREBASE_PROJECT_ID: process.env.FIREBASE_PROJECT_ID,
    },
    android,
  };
};

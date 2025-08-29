import { ExpoConfig } from "@expo/config";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  const android: ExpoConfig["android"] = {
    ...config.android,
    package: "com.yourco.driverAA",
    googleServicesFile: "android/app/google-services.json",
  };

  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    scheme: "driver",
    plugins: [
      ...(config.plugins ?? []),
      [
        "expo-build-properties",
        {
          android: {
            compileSdkVersion: 35,
            targetSdkVersion: 34,
            kotlinVersion: "1.9.25",
          },
        },
      ],
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

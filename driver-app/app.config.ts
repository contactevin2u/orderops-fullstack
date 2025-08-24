import { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DriverApp",
  slug: "driver-app",
  version: "1.0.0",
  orientation: "portrait",
  assetBundlePatterns: ["**/*"],

  android: {
    // MUST match package_name inside driver-app/google-services.json
    package: "com.yourco.driverAA",
    googleServicesFile: "./google-services.json",
    permissions: ["POST_NOTIFICATIONS"],
  },

  // plugins we rely on
  plugins: [
    ["expo-splash-screen", { backgroundColor: "#FFFFFF", resizeMode: "contain" }],
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
  ],

  // optional mirror (plugin reads it too)
  splash: { backgroundColor: "#FFFFFF", resizeMode: "contain" },

  // backend URL for the app
  extra: {
    apiBase: process.env.API_BASE || "https://orderops-api-v1.onrender.com",
  },

  runtimeVersion: { policy: "sdkVersion" },
});

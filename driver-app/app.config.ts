// driver-app/app.config.ts
import { ConfigContext, ExpoConfig } from "expo/config";

/**
 * DriverApp (Android-only) — splash plugin enabled.
 * Ensure google-services.json exists at: driver-app/google-services.json
 */
export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DriverApp",
  slug: "driver-app",
  version: "1.0.0",
  orientation: "portrait",
  assetBundlePatterns: ["**/*"],

  // Android config
  android: {
    // IMPORTANT: Must match package_name inside google-services.json
    package: "com.yourco.driverAA",
    googleServicesFile: "./google-services.json",
    permissions: ["POST_NOTIFICATIONS"],
  },

  // Expo plugins
  plugins: [
    // Makes/resolves splash resources, including @color/splashscreen_background
    ["expo-splash-screen", { backgroundColor: "#FFFFFF", resizeMode: "contain" }],
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
  ],

  // Optional – also set splash in config (plugin reads this too)
  splash: {
    backgroundColor: "#FFFFFF",
    resizeMode: "contain",
    // image: "./assets/splash.png", // add later if you have one
  },

  // Expose backend URL
  extra: {
    apiBase: process.env.API_BASE || "https://orderops-api-v1.onrender.com",
  },

  runtimeVersion: { policy: "sdkVersion" },
});

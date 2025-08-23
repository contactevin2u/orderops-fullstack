// driver-app/app.config.ts
import { ConfigContext, ExpoConfig } from "expo/config";

/**
 * Expo app config for the Driver App (Android-only).
 * - Place google-services.json at: driver-app/google-services.json
 * - android.package MUST match the package inside google-services.json.
 * - API base URL can be overridden in CI via env var API_BASE.
 */
export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DriverApp",
  slug: "driver-app",
  version: "1.0.0",
  orientation: "portrait",
  assetBundlePatterns: ["**/*"],

  // ---- ANDROID ONLY ----
  android: {
    // TODO: change this to your real package ID (must match google-services.json)
    package: "com.yourco.driverAA",
    googleServicesFile: "./google-services.json",
    // Request Android 13+ notifications permission at runtime in your app code
    permissions: ["POST_NOTIFICATIONS"],
  },

  // React Native Firebase config plugins (no manual Gradle edits needed)
  plugins: [
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
  ],

  // Expose your backend base URL to the app
  extra: {
    apiBase: process.env.API_BASE || "https://orderops-api-v1.onrender.com",
  },

  // Let OTA updates follow SDK by default (safe default)
  runtimeVersion: { policy: "sdkVersion" },
});

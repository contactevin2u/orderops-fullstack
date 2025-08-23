import { ConfigContext, ExpoConfig } from "expo/config";

/**
 * DriverApp (Android-only) with splash plugin enabled.
 * Ensure google-services.json exists at: driver-app/google-services.json
 */
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

  // Splash plugin generates @color/splashscreen_background, etc.
  plugins: [
    ["expo-splash-screen", { backgroundColor: "#FFFFFF", resizeMode: "contain" }],
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
  ],

  // Optional splash (plugin also reads this)
  splash: {
    backgroundColor: "#FFFFFF",
    resizeMode: "contain",
    // image: "./assets/splash.png",
  },

  extra: {
    apiBase: process.env.API_BASE || "https://orderops-api-v1.onrender.com",
  },

  runtimeVersion: { policy: "sdkVersion" },
});

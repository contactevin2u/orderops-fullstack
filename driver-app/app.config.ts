import 'dotenv/config';

export default ({ config }) => ({
  ...config,
  name: config?.name ?? "Driver",
  slug: config?.slug ?? "driver-app",
  scheme: config?.scheme ?? "driver",
  owner: config?.owner ?? undefined,

  android: {
    package: "com.yourco.driverAA",
    // IMPORTANT: source is project root; plugin copies it into android/app
    googleServicesFile: "./google-services.json",
    // keep default expo gradle settings; don't hardcode AGP/Kotlin here
  },

  extra: {
    // USE EXACT UPPER_CASE KEYS (your app reads these)
    API_BASE: process.env.API_BASE ?? "",
    FIREBASE_PROJECT_ID: process.env.FIREBASE_PROJECT_ID ?? "",
    FIREBASE_ANDROID_APP_ID: process.env.FIREBASE_ANDROID_APP_ID ?? "",
    // keep available for tooling if needed later:
    FIREBASE_SERVICE_ACCOUNT_JSON: process.env.FIREBASE_SERVICE_ACCOUNT_JSON ?? "",
  },

  experiments: {
    tsconfigPaths: true
  },

  plugins: [
    // DO NOT register "@notifee/react-native" as a config plugin here.
    // Notifee works without a config plugin for compile; the plugin was causing ESM/typeof errors.
    // If there is "@notifee/react-native" in plugins now, REMOVE it.
  ],
});


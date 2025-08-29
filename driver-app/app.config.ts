// driver-app/app.config.ts
import 'dotenv/config';
import type { ExpoConfig } from '@expo/config';

const pkg = 'com.yourco.driverAA';

const config: ExpoConfig = {
  name: 'Driver',
  slug: 'driver',
  scheme: 'driver',
  version: '1.0.0',
  orientation: 'portrait',
  icon: './assets/icon.png',
  userInterfaceStyle: 'light',
  splash: { image: './assets/splash.png', resizeMode: 'contain', backgroundColor: '#ffffff' },
  ios: { supportsTablet: false },
  android: {
    package: pkg,
    googleServicesFile: 'android/app/google-services.json',
    adaptiveIcon: { foregroundImage: './assets/adaptive-icon.png', backgroundColor: '#ffffff' },
    permissions: [],
  },
  web: { favicon: './assets/favicon.png' },
  // IMPORTANT: expose UPPER_CASE keys because the app code reads them
  extra: {
    API_BASE: process.env.API_BASE ?? '',
    FIREBASE_PROJECT_ID: process.env.FIREBASE_PROJECT_ID ?? '',
    FIREBASE_ANDROID_APP_ID: process.env.FIREBASE_ANDROID_APP_ID ?? '',
    FIREBASE_SERVICE_ACCOUNT_JSON: process.env.FIREBASE_SERVICE_ACCOUNT_JSON ?? '',
    GOOGLE_SERVICES_JSON: process.env.GOOGLE_SERVICES_JSON ?? '',
    eas: { projectId: process.env.EAS_PROJECT_ID ?? '' }, // optional
  },
  plugins: [
    // Keep Firebase plugin if you use @react-native-firebase/app.
    // It needs android.googleServicesFile to be set as above.
    '@react-native-firebase/app',
    // DO NOT include '@notifee/react-native' here (it’s not a config plugin).
  ],
};

export default config;

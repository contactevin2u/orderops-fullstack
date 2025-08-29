// driver-app/app.config.ts
import { ConfigContext, ExpoConfig } from '@expo/config';

export default ({ config }: ConfigContext): ExpoConfig => {
  const {
    API_BASE,
    FIREBASE_PROJECT_ID,
    FIREBASE_ANDROID_APP_ID,
    FIREBASE_SERVICE_ACCOUNT_JSON,
  } = process.env;

  const required = {
    API_BASE,
    FIREBASE_PROJECT_ID,
    FIREBASE_ANDROID_APP_ID,
    FIREBASE_SERVICE_ACCOUNT_JSON,
  };

  for (const [k, v] of Object.entries(required)) {
    if (!v) throw new Error(`Missing required env: ${k}`);
  }

  return {
    ...config,
    name: 'Driver App',
    slug: 'driver-app',
    version: '1.0.0',
    scheme: 'driver',
    android: {
      package: 'com.yourco.driverAA',
      googleServicesFile: 'android/app/google-services.json',
      adaptiveIcon: { foregroundImage: './assets/adaptive-icon.png', backgroundColor: '#FFFFFF' },
    },
    plugins: [
      '@react-native-firebase/app', // applies google-services and copies file during prebuild
      // DO NOT add '@notifee/react-native' here (no config plugin)
    ],
    extra: {
      API_BASE,
      FIREBASE_PROJECT_ID,
      FIREBASE_ANDROID_APP_ID,
      FIREBASE_SERVICE_ACCOUNT_JSON,
    },
  };
};

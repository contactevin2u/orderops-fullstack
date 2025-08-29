export default ({ config }: any) => ({
  ...config,
  name: 'driver-app',
  slug: 'driver-app',
  android: {
    // Source file in project root; Expo copies to android/app/ during prebuild
    googleServicesFile: 'google-services.json',
    package: 'com.yourco.driverAA',
  },
  extra: {
    // Canonical UPPER_CASE (what app should read)
    API_BASE: process.env.API_BASE ?? '',
    FIREBASE_PROJECT_ID: process.env.FIREBASE_PROJECT_ID ?? '',
    FIREBASE_ANDROID_APP_ID: process.env.FIREBASE_ANDROID_APP_ID ?? '',
    // Back-compat camelCase
    apiBase: process.env.API_BASE ?? '',
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID ?? '',
    firebaseAndroidAppId: process.env.FIREBASE_ANDROID_APP_ID ?? '',
  },
  plugins: [
    // Let Expo manage Kotlin & AGP; just set SDK levels
    ['expo-build-properties', { android: { compileSdkVersion: 35, targetSdkVersion: 34 } }],
    '@react-native-firebase/app',
    '@react-native-firebase/messaging',
  ],
});

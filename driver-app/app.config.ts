export default ({ config }: any) => ({
  ...config,
  name: "driver-app",
  slug: "driver-app",
  android: {
    // We materialize this file at android/app/google-services.json in CI
    googleServicesFile: "android/app/google-services.json",
    package: "com.orderops.driver"
  },
  extra: {
    apiBase: process.env.API_BASE ?? "",
    firebaseProjectId: process.env.FIREBASE_PROJECT_ID ?? "",
    firebaseAndroidAppId: process.env.FIREBASE_ANDROID_APP_ID ?? ""
  },
  plugins: [
    // Pin Android toolchain so prebuild doesn't drift
    ['expo-build-properties', { android: { compileSdkVersion: 35, targetSdkVersion: 34, kotlinVersion: '1.9.25' } }],
    '@react-native-firebase/app',
    '@react-native-firebase/messaging',
  ],
});

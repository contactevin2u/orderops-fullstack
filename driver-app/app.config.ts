// app.config.ts
import { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DriverApp",
  slug: "driver-app",
  android: {
    package: "com.yourco.driver",            // <-- change to your actual package ID
    googleServicesFile: "./google-services.json",
  },
  plugins: [
    "@react-native-firebase/app",
    "@react-native-firebase/messaging",
  ],
  extra: {
    apiBase: process.env.API_BASE || "https://orderops-api-v1.onrender.com",
  },
});

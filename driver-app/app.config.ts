import { ExpoConfig } from "@expo/config";
import fs from "fs";
import path from "path";

export default ({ config }: { config: ExpoConfig }): ExpoConfig => {
  const googleServices = process.env.GOOGLE_SERVICES_JSON;
  const android: ExpoConfig["android"] = {
    ...config.android,
    package: "com.yourco.driverAA",
  };

  if (googleServices) {
    const googleServicesPath = path.resolve(__dirname, "google-services.json");
    fs.writeFileSync(googleServicesPath, Buffer.from(googleServices, "base64"));
    android.googleServicesFile = "./google-services.json";
  }

  return {
    ...config,
    name: "DriverApp",
    slug: "driver-app",
    scheme: "driver",
    plugins: [
      ...(config.plugins ?? []),
      "@react-native-firebase/app",
      "@react-native-firebase/messaging",
      "@notifee/react-native",
    ],
    extra: {
      API_BASE: process.env.API_BASE || process.env.EXPO_PUBLIC_API_BASE,
    },
    android,
  };
};

import { ConfigContext, ExpoConfig } from "expo/config";

export default ({ config }: ConfigContext): ExpoConfig => ({
  ...config,
  name: "DriverApp",
  slug: "driver-app",
  ios: { bundleIdentifier: "com.yourco.driver" },
  android: { package: "com.yourco.driver" },
});

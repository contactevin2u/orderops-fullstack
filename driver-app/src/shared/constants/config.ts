import Constants from "expo-constants";

// Resolve API_BASE from environment variables or Expo config in order of precedence.
export const API_BASE = (() => {
  const fromEnv = process.env.API_BASE;
  const fromExpoPublic = process.env.EXPO_PUBLIC_API_BASE;
  const fromConfig = (Constants.expoConfig?.extra as any)?.API_BASE;
  const value = fromEnv ?? fromExpoPublic ?? fromConfig;
  if (!value) {
    throw new Error(
      "API_BASE is not configured. Set API_BASE or EXPO_PUBLIC_API_BASE in your environment or app.config.ts"
    );
  }
  return value as string;
})();


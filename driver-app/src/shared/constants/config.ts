import Constants from "expo-constants";

export const API_BASE = (() => {
  const fromEnv = process.env.API_BASE;
  const fromConfig = (Constants.expoConfig?.extra as any)?.API_BASE;
  const value = fromEnv ?? fromConfig;
  if (!value) {
    throw new Error("API_BASE is not set");
  }
  return value as string;
})();

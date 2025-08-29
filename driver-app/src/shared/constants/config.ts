import Constants from "expo-constants";

export const API_BASE = (() => {
  const fromEnv = process.env.API_BASE;
  const fromConfig =
    (Constants.expoConfig?.extra as any)?.API_BASE ??
    (Constants.manifest?.extra as any)?.API_BASE;
  const value = fromEnv ?? fromConfig;

  if (!value) {
    if (__DEV__) {
      console.warn(
        "API_BASE missing; set API_BASE in CI or app.config.ts extra."
      );
    }
    return "https://__MISSING_API_BASE__";
  }
  return String(value);
})();

export const FIREBASE_PROJECT_ID = (() => {
  const envVal = process.env.FIREBASE_PROJECT_ID;
  const cfgVal =
    (Constants.expoConfig?.extra as any)?.FIREBASE_PROJECT_ID ??
    (Constants.manifest?.extra as any)?.FIREBASE_PROJECT_ID;
  return String(envVal ?? cfgVal ?? "");
})();

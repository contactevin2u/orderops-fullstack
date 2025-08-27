let Constants: any;
try {
  Constants = require('expo-constants').default;
} catch {
  Constants = { expoConfig: { extra: { API_BASE: process.env.API_BASE, FIREBASE_PROJECT_ID: process.env.FIREBASE_PROJECT_ID } } };
}

export const API_BASE = (() => {
  const v = Constants.expoConfig?.extra?.API_BASE as string | undefined;
  if (!v) throw new Error('Missing API_BASE in app config');
  return v.replace(/\/+$/, '');
})();

export const FIREBASE_PROJECT_ID = (() => {
  const v = Constants.expoConfig?.extra?.FIREBASE_PROJECT_ID as string | undefined;
  if (!v) throw new Error('Missing FIREBASE_PROJECT_ID in app config');
  return v;
})();


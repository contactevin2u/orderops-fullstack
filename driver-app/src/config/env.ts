import Constants from 'expo-constants';

const API_BASE = (Constants.expoConfig?.extra as any)?.API_BASE;
if (!API_BASE) {
  throw new Error('Missing API_BASE environment value');
}

export { API_BASE };

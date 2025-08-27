import { useEffect, useState } from 'react';
import * as Network from 'expo-network';
import { AppState } from 'react-native';

export function useNetwork() {
  const [online, setOnline] = useState(true);

  const check = async () => {
    try {
      const st = await Network.getNetworkStateAsync();
      setOnline(!!st.isConnected && st.isInternetReachable !== false);
    } catch {
      setOnline(false);
    }
  };

  useEffect(() => {
    check();
    const sub = AppState.addEventListener('change', (s) => {
      if (s === 'active') check();
    });
    return () => sub.remove();
  }, []);

  return { online };
}


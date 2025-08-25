import React from 'react';
import { usePushNotifications } from './hooks/usePushNotifications';

export default function DriverSWManager() {
  const { enablePush } = usePushNotifications();

  React.useEffect(() => {
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker
        .register('/driver/sw/driver-sw.js')
        .catch(() => {});
    }
  }, []);

  // placeholder hook usage to avoid unused warnings
  React.useEffect(() => {
    // could trigger enablePush based on user interaction elsewhere
    void enablePush;
  }, [enablePush]);

  return null;
}

import React from 'react';
import { View, Text } from 'react-native';

interface Props {
  online: boolean;
  pendingCount: number;
}

export function OfflineBanner({ online, pendingCount }: Props) {
  if (online && pendingCount === 0) return null;

  const message = !online
    ? pendingCount > 0
      ? `Offline (${pendingCount} pending)`
      : 'Offline'
    : `Syncing ${pendingCount} change${pendingCount === 1 ? '' : 's'}...`;

  return (
    <View style={{ backgroundColor: '#fef3c7', padding: 8 }}>
      <Text style={{ color: '#92400e', textAlign: 'center', fontSize: 12 }}>{message}</Text>
    </View>
  );
}


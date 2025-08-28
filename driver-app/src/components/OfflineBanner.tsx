import React from 'react';
import { View, Text } from 'react-native';

export const OfflineBanner = ({ online, pendingCount }: { online: boolean; pendingCount: number }) => {
  if (online && pendingCount === 0) return null;
  return (
    <View style={{ backgroundColor: '#FFF3CD', padding: 8 }}>
      <Text style={{ color: '#664D03', fontWeight: '600' }}>
        {online ? `Syncing pending actions: ${pendingCount}` : `Offline — ${pendingCount} action(s) queued`}
      </Text>
    </View>
  );
};


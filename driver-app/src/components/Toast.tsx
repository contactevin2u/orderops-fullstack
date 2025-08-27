import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet } from 'react-native';

type Variant = 'error' | 'info' | 'success';

interface ToastState {
  message: string;
  variant: Variant;
}

let showHandler: ((msg: string, variant: Variant) => void) | null = null;

export const toast = {
  show(message: string, variant: Variant = 'info') {
    showHandler?.(message, variant);
  },
};

export default function Toast() {
  const [state, setState] = useState<ToastState | null>(null);

  useEffect(() => {
    showHandler = (message, variant) => {
      setState({ message, variant });
      setTimeout(() => setState(null), 3500);
    };
    return () => {
      showHandler = null;
    };
  }, []);

  if (!state) return null;
  const bg =
    state.variant === 'error' ? '#dc2626' : state.variant === 'success' ? '#16a34a' : '#2563eb';
  return (
    <View style={[styles.container, { backgroundColor: bg }]} pointerEvents="none">
      <Text style={styles.text}>{state.message}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    position: 'absolute',
    top: 40,
    alignSelf: 'center',
    paddingHorizontal: 16,
    paddingVertical: 8,
    borderRadius: 4,
    zIndex: 1000,
  },
  text: { color: '#fff' },
});


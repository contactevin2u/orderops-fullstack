import React, { useState } from 'react';
import { View, Text, TextInput, Pressable } from 'react-native';
import { useAuth } from '../hooks/useAuth';

export default function Login() {
  const { signIn, loading } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState<string | null>(null);

  const handle = async () => {
    setError(null);
    try {
      await signIn(email, password);
    } catch (e: any) {
      setError(e?.message ?? String(e));
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Driver Login</Text>
      <TextInput
        style={styles.input}
        placeholder="Email"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
        returnKeyType="done"
        onSubmitEditing={handle}
      />
      {error && <Text style={styles.error}>Error: {error}</Text>}
      <Pressable onPress={handle} disabled={loading} style={[styles.button, loading && { opacity: 0.5 }]}>
        <Text style={styles.buttonText}>{loading ? 'Signing In…' : 'Sign In'}</Text>
      </Pressable>
    </View>
  );
}

const styles = {
  container: {
    flexGrow: 1 as const,
    padding: 16,
    justifyContent: 'center' as const,
    backgroundColor: '#f0f9ff',
  },
  title: {
    fontSize: 22,
    fontWeight: '700',
    textAlign: 'center' as const,
    marginBottom: 16,
    color: '#0f172a',
  },
  input: {
    borderWidth: 1,
    borderColor: '#93c5fd',
    backgroundColor: '#fff',
    borderRadius: 4,
    padding: 8,
    marginBottom: 12,
  },
  button: {
    backgroundColor: '#3b82f6',
    paddingVertical: 10,
    paddingHorizontal: 14,
    borderRadius: 8,
    alignItems: 'center' as const,
  },
  buttonText: { color: '#fff', fontWeight: '600' as const },
  error: { marginTop: 12, color: '#b00020' },
};

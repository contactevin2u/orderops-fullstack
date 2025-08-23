import React from 'react';
import { SafeAreaView, FlatList, Text } from 'react-native';
import { useOrderStore } from './src/stores/orderStore';
import OrderItem from './src/components/OrderItem';

export default function App() {
  const orders = useOrderStore((s) => s.orders);

  return (
    <SafeAreaView style={{ flex: 1 }}>
      <Text style={{ fontSize: 24, textAlign: 'center', marginVertical: 20 }}>
        Assigned Orders
      </Text>
      <FlatList
        data={orders}
        keyExtractor={(item) => item.id}
        renderItem={({ item }) => <OrderItem order={item} />}
      />
    </SafeAreaView>
  );
}

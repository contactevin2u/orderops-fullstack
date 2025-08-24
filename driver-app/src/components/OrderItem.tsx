import React from 'react';
import { View, Text } from 'react-native';
import { Order } from '../stores/orderStore';

interface Props {
  order: Order;
}

export default function OrderItem({ order }: Props) {
  return (
    <View style={{ padding: 12, borderBottomWidth: 1, borderColor: '#ccc' }}>
      <Text style={{ fontWeight: 'bold' }}>{order.description}</Text>
      <Text>Status: {order.status}</Text>
    </View>
  );
}

import React from 'react';
import { View, Text } from 'react-native';
import OrderItem from './OrderItem';
import { Order } from '../stores/orderStore';

interface Props {
  orders: Order[];
  onUpdate: (id: number, status: string) => void;
  onComplete: (id: number) => void;
}

export default function OrdersList({ orders, onUpdate, onComplete }: Props) {
  if (!orders.length) {
    return <Text>No orders.</Text>;
  }
  return (
    <View>
      {orders.map((o) => (
        <OrderItem key={o.id} order={o} onUpdate={(s) => onUpdate(o.id, s)} onComplete={() => onComplete(o.id)} />
      ))}
    </View>
  );
}

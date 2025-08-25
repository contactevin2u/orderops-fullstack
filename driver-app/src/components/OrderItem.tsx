import React, { useState } from 'react';
import { View, Text, Button, Pressable } from 'react-native';
import { Order } from '../stores/orderStore';

interface Props {
  order: Order;
  token: string;
  apiBase: string;
  refresh: () => void;
}

export default function OrderItem({ order, token, apiBase, refresh }: Props) {
  const [expanded, setExpanded] = useState(false);
  const update = async (status: string) => {
    try {
      await fetch(`${apiBase}/drivers/orders/${order.id}`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ status }),
      });
      refresh();
    } catch {}
  };

  return (
    <View style={{ padding: 12, borderBottomWidth: 1, borderColor: '#ccc' }}>
      <Pressable onPress={() => setExpanded((e) => !e)}>
        <Text style={{ fontWeight: 'bold' }}>{order.description}</Text>
      </Pressable>
      <Text>Status: {order.status}</Text>
      {expanded &&
        order.items?.map((item) => (
          <Text key={item.id}>
            • {item.qty} x {item.name}
          </Text>
        ))}
      {order.status === 'ASSIGNED' && (
        <Button title="Start" onPress={() => update('IN_TRANSIT')} />
      )}
      {order.status === 'IN_TRANSIT' && (
        <Button title="Complete" onPress={() => update('DELIVERED')} />
      )}
    </View>
  );
}

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
  const statusColors: Record<string, string> = {
    ASSIGNED: '#2563eb',
    IN_TRANSIT: '#16a34a',
    ON_HOLD: '#dc2626',
    DELIVERED: '#6b7280',
  };
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
    <View
      style={{
        padding: 12,
        borderWidth: 1,
        borderColor: '#e5e7eb',
        backgroundColor: '#fff',
        borderRadius: 8,
        marginBottom: 12,
      }}
    >
      <Pressable onPress={() => setExpanded((e) => !e)}>
        <Text style={{ fontWeight: 'bold', color: '#0f172a' }}>
          {order.address || order.description}
        </Text>
      </Pressable>
      {expanded && (
        <>
          <Text
            style={{
              color: '#fff',
              backgroundColor: statusColors[order.status] || '#6b7280',
              paddingHorizontal: 8,
              paddingVertical: 2,
              borderRadius: 4,
              alignSelf: 'flex-start',
              marginVertical: 4,
            }}
          >
            {order.status}
          </Text>
          {order.phone && <Text>Phone: {order.phone}</Text>}
          {order.total !== undefined && <Text>Total: {order.total}</Text>}
          {order.items?.map((item) => (
            <Text key={item.id}>
              • {item.qty} x {item.name}
            </Text>
          ))}
          {order.status === 'ASSIGNED' && (
            <>
              <Button title="Start" onPress={() => update('IN_TRANSIT')} />
              <Button title="Hold" onPress={() => update('ON_HOLD')} />
            </>
          )}
          {order.status === 'IN_TRANSIT' && (
            <>
              <Button title="Complete" onPress={() => update('DELIVERED')} />
              <Button title="Hold" onPress={() => update('ON_HOLD')} />
            </>
          )}
          {order.status === 'ON_HOLD' && (
            <Button title="Resume" onPress={() => update('IN_TRANSIT')} />
          )}
        </>
      )}
    </View>
  );
}

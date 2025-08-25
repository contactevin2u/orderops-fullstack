// OrderItem.tsx
import React, { useState } from 'react';
import { View, Text, Button, Pressable, Linking } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import * as ImageManipulator from 'expo-image-manipulator';
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
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
        body: JSON.stringify({ status }),
      });
      refresh();
    } catch (e) {
      // swallow
    }
  };

  async function completeWithPhoto() {
    const res = await ImagePicker.launchCameraAsync({ allowsEditing: false, quality: 0.7 });
    if (res.canceled) return;
    const asset = res.assets[0];
    const manip = await ImageManipulator.manipulateAsync(
      asset.uri,
      [{ resize: { width: 1280 } }],
      { compress: 0.7, format: ImageManipulator.SaveFormat.JPEG }
    );
    const form = new FormData();
    form.append('file', { uri: manip.uri, type: 'image/jpeg', name: 'pod.jpg' } as any);
    await fetch(`${apiBase}/drivers/orders/${order.id}/pod-photo`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: form,
    });
    await update('DELIVERED');
  }

  const title = order.code || order.description || `Order #${order.id}`;
  const cust = order.customer || {};

  return (
    <View style={{ padding: 12, borderWidth: 1, borderColor: '#e5e7eb', backgroundColor: '#fff', borderRadius: 8, marginBottom: 12 }}>
      <Pressable onPress={() => setExpanded(e => !e)}>
        <Text style={{ fontWeight: 'bold', color: '#0f172a' }}>{title}</Text>
      </Pressable>

      {expanded && (
        <>
          <Text style={{
            color: '#fff',
            backgroundColor: statusColors[order.status] || '#6b7280',
            paddingHorizontal: 8, paddingVertical: 2, borderRadius: 4,
            alignSelf: 'flex-start', marginVertical: 4,
          }}>
            {order.status}
          </Text>

          {!!cust.name && <Text>Customer: {cust.name}</Text>}
          {!!cust.phone && (
            <Text onPress={() => Linking.openURL(`tel:${cust.phone}`)} style={{ textDecorationLine: 'underline' }}>
              Phone: {cust.phone} (Tap to call)
            </Text>
          )}
          {!!cust.address && <Text>Address: {cust.address}</Text>}
          {!!cust.map_url && (
            <Text onPress={() => Linking.openURL(String(cust.map_url))} style={{ textDecorationLine: 'underline' }}>
              Open Map
            </Text>
          )}

          {!!order.delivery_date && <Text>Delivery: {String(order.delivery_date).slice(0, 10)}</Text>}
          {!!order.notes && <Text>Notes: {order.notes}</Text>}

          {order.items?.length ? (
            <>
              <Text style={{ marginTop: 6, fontWeight: '600' }}>Items</Text>
              {order.items.map(it => (
                <Text key={it.id}>• {it.qty} x {it.name}{typeof it.line_total !== 'undefined' ? ` — RM ${Number(it.line_total).toFixed(2)}` : ''}</Text>
              ))}
            </>
          ) : null}

          <View style={{ marginTop: 6 }}>
            {!!order.subtotal && <Text>Subtotal: RM {Number(order.subtotal).toFixed(2)}</Text>}
            {!!order.delivery_fee && <Text>Delivery Fee: RM {Number(order.delivery_fee).toFixed(2)}</Text>}
            {!!order.return_delivery_fee && <Text>Return Delivery: RM {Number(order.return_delivery_fee).toFixed(2)}</Text>}
            {!!order.penalty_fee && <Text>Penalty: RM {Number(order.penalty_fee).toFixed(2)}</Text>}
            {!!order.discount && <Text>Discount: RM {Number(order.discount).toFixed(2)}</Text>}
            {!!order.total && <Text>Total: RM {Number(order.total).toFixed(2)}</Text>}
            {!!order.paid_amount && <Text>Paid: RM {Number(order.paid_amount).toFixed(2)}</Text>}
            {!!order.balance && <Text>Balance: RM {Number(order.balance).toFixed(2)}</Text>}
          </View>

          {order.status === 'ASSIGNED' && (
            <>
              <Button title="Start" onPress={() => update('IN_TRANSIT')} />
              <Button title="Hold" onPress={() => update('ON_HOLD')} />
            </>
          )}
          {order.status === 'IN_TRANSIT' && (
            <>
              <Button title="Complete" onPress={completeWithPhoto} />
              <Button title="Hold" onPress={() => update('ON_HOLD')} />
            </>
          )}
          {order.status === 'ON_HOLD' && <Button title="Resume" onPress={() => update('IN_TRANSIT')} />}
        </>
      )}
    </View>
  );
}


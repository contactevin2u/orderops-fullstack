import React from 'react';
import { View, Text, Button, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Order, useOrderStore } from '../stores/orderStore';

interface Props {
  order: Order;
}

export default function OrderItem({ order }: Props) {
  const completeOrder = useOrderStore((s) => s.completeOrder);

  const handleComplete = async () => {
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: false,
      quality: 0.5,
    });
    if (!result.canceled) {
      const uri = result.assets[0].uri;
      // In a full implementation, upload to remote storage here
      completeOrder(order.id, uri);
    }
  };

  const commission = order.initialPayment * order.commissionRate;

  return (
    <View style={{ padding: 12, borderBottomWidth: 1, borderColor: '#ccc' }}>
      <Text style={{ fontWeight: 'bold' }}>{order.description}</Text>
      <Text>Drivers: {order.assignedDrivers.join(', ')}</Text>
      <Text>Status: {order.status}</Text>
      <Text>Commission: ${commission.toFixed(2)}</Text>
      {order.photoUrl && (
        <Image
          source={{ uri: order.photoUrl }}
          style={{ width: 100, height: 100, marginTop: 8 }}
        />
      )}
      {order.status !== 'completed' && (
        <Button title="Complete with Photo" onPress={handleComplete} />
      )}
    </View>
  );
}

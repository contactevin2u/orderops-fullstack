import React from 'react';
import { View, Text, Button, Image } from 'react-native';
import * as ImagePicker from 'expo-image-picker';
import { Trip, useTripStore } from '../stores/tripStore';

interface Props {
  trip: Trip;
  token: string;
}

export default function TripItem({ trip, token }: Props) {
  const update = useTripStore((s) => s.updateStatus);

  const handleStart = () => update(token, trip.id, 'start');

  const handleDeliver = async () => {
    const result = await ImagePicker.launchCameraAsync({
      allowsEditing: false,
      quality: 0.5,
    });
    if (!result.canceled) {
      const uri = result.assets[0].uri;
      await update(token, trip.id, 'deliver', uri);
    }
  };

  const handleFail = () => update(token, trip.id, 'fail');

  return (
    <View style={{ padding: 12, borderBottomWidth: 1, borderColor: '#ccc' }}>
      <Text style={{ fontWeight: 'bold' }}>Trip #{trip.id}</Text>
      <Text>Status: {trip.status}</Text>
      {trip.pod_photo_url && (
        <Image
          source={{ uri: trip.pod_photo_url }}
          style={{ width: 100, height: 100, marginTop: 8 }}
        />
      )}
      <View style={{ flexDirection: 'row', marginTop: 8 }}>
        {trip.status === 'ASSIGNED' && (
          <Button title="Start" onPress={handleStart} />
        )}
        {trip.status !== 'DELIVERED' && (
          <View style={{ marginLeft: 8 }}>
            <Button title="Deliver" onPress={handleDeliver} />
          </View>
        )}
        {trip.status !== 'FAILED' && (
          <View style={{ marginLeft: 8 }}>
            <Button title="Fail" onPress={handleFail} />
          </View>
        )}
      </View>
    </View>
  );
}

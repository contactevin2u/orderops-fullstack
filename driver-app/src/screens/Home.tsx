import React, { useState } from 'react';
import { ScrollView, View, Text, Pressable, RefreshControl } from 'react-native';
import { useAuth } from '../hooks/useAuth';
import { useOrders } from '../hooks/useOrders';
import OrdersList from '../components/OrdersList';
import { useNetwork } from '../hooks/useNetwork';
import { useOutbox } from '../offline/useOutbox';
import { OfflineBanner } from '../components/OfflineBanner';

export default function Home() {
  const { signOut } = useAuth();
  const { orders, refresh, update, completeWithPhoto } = useOrders();
  const { online } = useNetwork();
  const { pendingCount } = useOutbox();
  const [tab, setTab] = useState<'active' | 'completed'>('active');
  const [refreshing, setRefreshing] = useState(false);

  const activeOrders = orders.filter((o) => o.status !== 'DELIVERED');
  const completedOrders = orders.filter((o) => o.status === 'DELIVERED');

  const onRefresh = async () => {
    setRefreshing(true);
    await refresh();
    setRefreshing(false);
  };

  const list = tab === 'active' ? activeOrders : completedOrders;

  return (
    <>
      <OfflineBanner online={online} pendingCount={pendingCount} />
      <ScrollView
        contentContainerStyle={{ padding: 16, backgroundColor: '#f0f9ff' }}
        refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} />}
      >
        <Pressable style={{ alignSelf: 'flex-end', padding: 4, marginBottom: 8 }} onPress={signOut}>
          <Text style={{ color: '#3b82f6', fontSize: 12, textDecorationLine: 'underline' }}>Sign Out</Text>
        </Pressable>

        <View style={{ flexDirection: 'row', marginBottom: 16 }}>
          <Pressable
            style={{
              flex: 1,
              paddingVertical: 8,
              borderBottomWidth: 2,
              borderColor: tab === 'active' ? '#3b82f6' : '#e5e7eb',
              alignItems: 'center',
            }}
            onPress={() => setTab('active')}
          >
            <Text
              style={{ color: tab === 'active' ? '#3b82f6' : '#64748b', fontWeight: tab === 'active' ? '600' : '400' }}
            >
              Active ({activeOrders.length})
            </Text>
          </Pressable>
          <Pressable
            style={{
              flex: 1,
              paddingVertical: 8,
              borderBottomWidth: 2,
              borderColor: tab === 'completed' ? '#3b82f6' : '#e5e7eb',
              alignItems: 'center',
            }}
            onPress={() => setTab('completed')}
          >
            <Text
              style={{ color: tab === 'completed' ? '#3b82f6' : '#64748b', fontWeight: tab === 'completed' ? '600' : '400' }}
            >
              Completed ({completedOrders.length})
            </Text>
          </Pressable>
        </View>

        <OrdersList orders={list} onUpdate={update} onComplete={completeWithPhoto} />
      </ScrollView>
    </>
  );
}

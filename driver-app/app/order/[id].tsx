import { View, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";
import { useOrders } from "../../src/presentation/hooks/useOrders";

export default function OrderDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { active, completed } = useOrders();
  const order = [...active, ...completed].find((o) => o.id.toString() === id);

  if (!order) {
    return <Text>Order not found</Text>;
  }

  return (
    <View>
      <Text>Order #{order.id}</Text>
      <Text>Status: {order.status}</Text>
      <Text>Customer: {order.customer.name}</Text>
    </View>
  );
}

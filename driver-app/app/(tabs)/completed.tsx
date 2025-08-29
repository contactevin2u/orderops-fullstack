import { View, Text } from "react-native";
import { useOrders } from "../../src/presentation/hooks/useOrders";

export default function CompletedTab() {
  const { completedOrders } = useOrders();
  return (
    <View>
      {completedOrders.map((o) => (
        <Text key={o.id}>Order #{o.id} - {o.customer.name}</Text>
      ))}
    </View>
  );
}

import { View, Text } from "react-native";
import { Link } from "expo-router";
import { useOrders } from "../../src/presentation/hooks/useOrders";

export default function ActiveTab() {
  const { active } = useOrders();
  return (
    <View>
      {active.map((o) => (
        <Link key={o.id} href={`/order/${o.id}`}>
          <Text>Order #{o.id} - {o.customer.name}</Text>
        </Link>
      ))}
    </View>
  );
}

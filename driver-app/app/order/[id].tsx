import { View, Text } from "react-native";
import { useLocalSearchParams } from "expo-router";

export default function OrderDetail() {
  const { id } = useLocalSearchParams<{ id: string }>();
  return (
    <View>
      <Text>Order {id}</Text>
    </View>
  );
}

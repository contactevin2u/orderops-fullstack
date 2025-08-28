import { Tabs } from "expo-router";

export default function TabsLayout() {
  return (
    <Tabs>
      <Tabs.Screen name="index" options={{ title: "Active" }} />
      <Tabs.Screen name="completed" options={{ title: "Completed" }} />
    </Tabs>
  );
}

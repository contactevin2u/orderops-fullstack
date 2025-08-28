import messaging from "@react-native-firebase/messaging";
// Register a headless handler for background messages
messaging().setBackgroundMessageHandler(async (message) => {
  // Optionally: prefetch orders or store a flag for UI invalidation
});

import messaging from "@react-native-firebase/messaging";

messaging().setBackgroundMessageHandler(async (message) => {
  // noop or TODO: prefetch orders
});

import { registerRootComponent } from 'expo';
import App from './App';
import messaging from '@react-native-firebase/messaging';

// background handler (required for notifications when app is quit)
messaging().setBackgroundMessageHandler(async (msg) => {
  if (msg?.data?.type === 'order_assigned') {
    console.log('Order assigned while app in background');
  }
});

registerRootComponent(App);

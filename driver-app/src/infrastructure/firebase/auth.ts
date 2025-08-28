import auth from '@react-native-firebase/auth';

export function signIn(email: string, password: string) {
  return auth().signInWithEmailAndPassword(email, password);
}

export function signOut() {
  return auth().signOut();
}

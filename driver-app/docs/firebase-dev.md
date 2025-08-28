# Firebase Local Development

1. Create a Firebase project and download `google-services.json`.
2. Copy it into `android/app/google-services.json`.
3. (Optional) For iOS, place `GoogleService-Info.plist` in the iOS project.
4. Install dependencies and run the app:

```
npm install
npm run android
```

The Android build expects the file to exist; without it, Expo may fail to run.


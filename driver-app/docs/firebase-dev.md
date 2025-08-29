# Firebase Local Development

1. Create a Firebase project and download `google-services.json`.
2. Place it at `driver-app/google-services.json`; Expo's `googleServicesFile` points to `./google-services.json`, and the plugin will copy it into `android/app`.
3. (Optional) For iOS, place `GoogleService-Info.plist` in the iOS project.
4. For CI, create one GitHub Secret `DRIVER_APP_ENV` with lines like:

```
GOOGLE_SERVICES_JSON='{"minified":"json","…":"…"}'
API_BASE=https://api.example.com
FIREBASE_PROJECT_ID=your-project-id
```

Use `jq -c . google-services.json` to produce the single-line JSON for `GOOGLE_SERVICES_JSON`. No base64 required.
5. Install dependencies and run the app:

```
npm install
npm run android
```

The Android build expects the file to exist; without it, Expo may fail to run.

# Firebase Local Development

1. Create a Firebase project and download `google-services.json`.
2. Place it at `driver-app/google-services.json`; Expo's `googleServicesFile` points to `./google-services.json`, and the plugin will copy it into `android/app`.
3. (Optional) For iOS, place `GoogleService-Info.plist` in the iOS project.
4. For CI, store environment variables in a single GitHub secret `DRIVER_APP_ENV` containing:

   ```
   GOOGLE_SERVICES_JSON='{"minified": "json"}'
   API_BASE=https://your.api
   FIREBASE_PROJECT_ID=your-project-id
   ```

   Minify the JSON with `jq -c . google-services.json`; no base64 needed.
5. Install dependencies and run the app:

```
npm install
npm run android
```

The Android build expects the file to exist; without it, Expo may fail to run.


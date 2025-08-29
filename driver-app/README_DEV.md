# Local Android Development

**Local dev:** place `google-services.json` in the project root (`driver-app/google-services.json`) and run the prebuild; the Firebase plugin will copy it into `android/app`.

**CI:** put a single GitHub Actions secret named `DRIVER_APP_ENV` containing:

```
GOOGLE_SERVICES_JSON='{"minified": "json"}'
API_BASE=https://your.api
FIREBASE_PROJECT_ID=your-project-id
```

Use `jq -c . google-services.json` to minify; no base64 needed.

1) Ensure `google-services.json` exists in the project root
2) Set `API_BASE` via `.env` or CLI
3) `npm ci`
4) `npx expo prebuild --platform android`
5) `cd android && ./gradlew assembleDebug` or `npm run android`


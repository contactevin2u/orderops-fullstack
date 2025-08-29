# Local Android Development

## Quick start

Local dev: place your real `driver-app/google-services.json` and run `npx expo prebuild`. The plugin will copy it into `android/app/`.

CI: create one GitHub Secret `DRIVER_APP_ENV` with lines like:

```
GOOGLE_SERVICES_JSON='{"minified":"json","…":"…"}'
API_BASE=https://api.example.com
FIREBASE_PROJECT_ID=your-project-id
```

Use `jq -c . google-services.json` to produce the single-line JSON for `GOOGLE_SERVICES_JSON`. No base64 required.

1) Ensure `google-services.json` exists in the project root
2) Set `API_BASE` via `.env` or CLI
3) `npm ci`
4) `npx expo prebuild --platform android`
5) `cd android && ./gradlew assembleDebug` or `npm run android`

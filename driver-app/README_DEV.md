# Local Android Development

1. Copy `android/app/google-services.json.example` to `android/app/google-services.json`.
2. Set `API_BASE` in `.env` or provide it on the CLI when running commands.
3. Install dependencies with `npm ci`.
4. Generate native Android project: `npx expo prebuild --platform android`.
5. Build and run:
   - `cd android && ./gradlew assembleDebug`, or
   - `npm run android`.

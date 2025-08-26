# Driver App

This directory contains the React Native driver application built with Expo.

## Building APKs

The repository includes GitHub Actions workflows that build Android packages
and upload them as artifacts:

- **driver-android-debug** – produces a debug APK for testing.
- **driver-android-release** – produces a release-signed APK suitable for
  distribution outside of Google Play. The workflow expects a
  `GOOGLE_SERVICES_JSON` secret containing your Firebase configuration.

Run either workflow from the Actions tab in GitHub and download the generated
APK from the workflow artifacts section.

## QA Checklist

Before testing builds, verify the following on the Android test device:

- Notifications are allowed for the app (Android 13+ requires explicit permission).
- Battery optimizations are disabled so background handlers can run.
- The Firebase SHA-1/256 keys are registered and a matching `google-services.json`
  with the same `package_name` is bundled with the app.

Test scenarios:

1. **App killed** – assign an order; a system notification appears within a few
   seconds. Tapping it opens the app with the orders list refreshed.
2. **Missed push while active** – block FCM or disable network; while the app is
   in the foreground, orders refresh within five minutes via polling.

Reinstalling or updating the app should continue to receive push notifications
thanks to automatic token refresh and re-registration.

